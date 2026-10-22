import sys,traceback
from pathlib import Path

if __name__=='__main__':
    if len(sys.argv)>=3 and sys.argv[1]=='--self-test':
        try:
            from app.verification import self_test
            self_test(Path(sys.argv[2]),live='--live' in sys.argv)
        except Exception:
            output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True);(output/'error.txt').write_text(traceback.format_exc(),encoding='utf-8');sys.exit(1)
    else:
        from app.main import main
        sys.exit(main())
