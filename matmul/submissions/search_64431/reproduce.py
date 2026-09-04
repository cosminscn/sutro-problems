"""Rebuild64,431 from the prior literal generator and five legal order edits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from matmul.submissions.search_64448 import reproduce as prior

reference=prior.reference
core=reference.core
MOVES=((7902,7905,2),(7893,7991,1),(1823,1825,1),(226,222,4),(1281,1287,1))
PARENT_RAW_SHA256='6dca745d2e7fff3e23794dc28c6481fde140bb522922ab34c06d9e2c3cfb089a'
EXPECTED={
    'reordered_generator':(1177063,'3c86365a522ca3909e8b1a892ef38e9edc21f3c54eb873f074854ff7e638be13'),
    'dp_initial':(64458,'0393e6775e7b73ea8f117dd541247a07f5e8de146359b2ac422cf87d9155f184'),
    'pair2_seed0_no_ties':(64431,'66929dab27c72e9714bf8a1ae77f1942b4201fe81d0d7a255a8547108eabadc3'),
    'pair5_seed11_ties':(64431,'9d94114a87fecd30168fbcf63931bbc98a50778984a11fe0c3b16940218bcf11'),
}
EXPECTED_HISTORY_SHA256={
    'pair2_seed0_no_ties':'a411d80daf8a946df039866dfe764c35223c5f1fb1e147e7e3c681ceb165cb22',
    'pair5_seed11_ties':'4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
}

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def generate():
    """Generate raw64448; change only order, before any address allocation."""
    p=prior.capture_b(prior.generate())
    assert sha(core.emit(p))==PARENT_RAW_SHA256
    frozen={op.dest:op for op in p.ops}
    for source,destination,length in MOVES:
        assert 0<=source<=len(p.ops)-length and 0<=destination<=len(p.ops)-length
        assert max(source,destination)+length-min(source,destination)<=128
        block=p.ops[source:source+length]
        del p.ops[source:source+length]
        p.ops[destination:destination]=block
        # Check the full order after every edit, including capture dependencies.
        seen=set(p.inputs)
        for op in p.ops:
            assert all(v in seen for v in op.src)
            assert op.dest not in seen and op==frozen[op.dest]
            seen.add(op.dest)
        assert len(p.ops)==len(frozen) and all(v in seen for v in p.outputs)
    assert sha(core.emit(p))==EXPECTED['reordered_generator'][1]
    return p

def reproduce(output=None,manifest=None):
    started=time.monotonic();stages=[]
    discovery=json.loads((HERE/'discovery.json').read_text())
    configuration=json.loads((HERE/'configuration.json').read_text())
    assert tuple((m['source'],m['destination'],m['length']) for m in configuration['moves'])==MOVES
    assert hashlib.sha256((HERE/'configuration.json').read_bytes()).hexdigest()==discovery['configuration_sha256']
    for relative,expected in discovery['helper_sha256'].items():
        assert hashlib.sha256((REPO/relative).read_bytes()).hexdigest()==expected,relative

    def checkpoint(name,p,history=None):
        ir=core.emit(p);proof=core.verify_ir(ir);expected_score,expected_hash=EXPECTED[name]
        assert proof['score']==expected_score and proof['sha256']==expected_hash,(name,proof)
        record=dict(name=name,**proof)
        if history is not None:
            history_hash=sha(json.dumps(history,sort_keys=True,separators=(',',':')))
            assert history_hash==EXPECTED_HISTORY_SHA256[name]
            assert history==discovery['accepted_histories'][name]
            record.update(accepted_history=history,history_sha256=history_hash)
        stages.append(record)
        print(json.dumps(dict(stage=name,score=expected_score,sha256=expected_hash)),flush=True)
        return ir

    p=generate();checkpoint('reordered_generator',p)
    p=reference.initial_allocation(p)
    p=core.parse_ir(checkpoint('dp_initial',p))
    for name,rounds,seed,ties in [('pair2_seed0_no_ties',2,0,False),('pair5_seed11_ties',5,11,True)]:
        # Match fixed-round discovery RNG with no machine-speed cutoff.
        p,history=reference.improve(p,rounds=rounds,seed=seed,max_seconds=float('inf'),allow_ties=ties,checkpoint=None)
        checkpoint(name,p,history)
    ir=core.emit(p)
    assert ir.encode()==(HERE.parent/'best_64431.ir').read_bytes(),'Replay differs from submission'
    if output is not None:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(ir)
    result=dict(score=64431,sha256=EXPECTED['pair5_seed11_ties'][1],fresh_process_replay=True,
        byte_identical_to_submission=True,accepted_histories_match_discovery=True,
        elapsed_seconds=time.monotonic()-started,configuration=configuration,
        versions=dict(python=platform.python_version(),numpy=reference.numpy.__version__,ortools=reference.ortools.__version__),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        discovery_configuration_sha256=hashlib.sha256((HERE/'configuration.json').read_bytes()).hexdigest(),
        discovery_sha256=hashlib.sha256((HERE/'discovery.json').read_bytes()).hexdigest(),
        helper_sha256=discovery['helper_sha256'],stages=stages)
    if manifest is not None:
        manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps(result,indent=2)+'\n')
    print('Portable generator replay is byte-identical to best_64431.ir.',flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path);parser.add_argument('--manifest',type=Path)
    args=parser.parse_args();reproduce(args.output,args.manifest)
