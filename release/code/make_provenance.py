"""Regenerate release/PROVENANCE.csv (wrapper for `python run.py provenance`; paths from config.yaml)."""
from stages.s00_provenance import main
if __name__ == '__main__':
    main()
