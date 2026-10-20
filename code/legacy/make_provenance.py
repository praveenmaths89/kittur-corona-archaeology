# Superseded. The original script resolved ROOT three levels up, which after the move to release/code/legacy pointed at
# release/ and wrote release/release/PROVENANCE.csv. Provenance is now stage 00 of the config-based pipeline:
#     cd release/code && python run.py provenance      (or python make_provenance.py)
import runpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
runpy.run_path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'make_provenance.py'), run_name='__main__')
