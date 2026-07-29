import multiprocessing as mp
import sys, traceback, pickle

mp.set_start_method("spawn", force=True)

def _child_import_scanner():
    # Esto corre DENTRO del worker (spawn). Si el import de scanner falla,
    # el proceso hijo muere y veremos el traceback real en stderr.
    import scanner  # noqa
    return "scanner import OK"

def _child_pickle_ctx():
    import scanner as s
    # Construir un ctx mínimo y probar picklability (causa ALTA #1)
    ctx = s.StratFEvalContext()
    try:
        blob = pickle.dumps(ctx)
        return ("pickle OK bytes=" + str(len(blob)))
    except Exception as e:
        return ("PICKLE FAIL: " + repr(e))

if __name__ == "__main__":
    # Test 1: import-time del worker
    print("=== TEST 1: import scanner dentro del worker (spawn) ===")
    try:
        with mp.Pool(processes=1) as pool:
            r = pool.apply(_child_import_scanner)
            print("RESULT:", r)
    except Exception:
        print("POOL ROTO en import-time. Traceback arriba (ver stderr del hijo).")

    # Test 2: picklability del ctx
    print("=== TEST 2: pickle.dumps(StratFEvalContext) ===")
    try:
        with mp.Pool(processes=1) as pool:
            r = pool.apply(_child_pickle_ctx)
            print("RESULT:", r)
    except Exception:
        print("POOL ROTO en pickle. Traceback arriba.")
