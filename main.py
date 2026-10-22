import sys
from pathlib import Path
import traceback

if __name__ == '__main__':
    if len(sys.argv)>=3 and sys.argv[1] in {'--self-test','--verify-package'}:
        output=Path(sys.argv[-1])
        try:
            if sys.argv[1]=='--self-test':
                from speccompare.verification import verify_suite
                verify_suite(output)
            else:
                from speccompare.verification import verify
                verify(sys.argv[2],output)
        except Exception:
            output.mkdir(parents=True,exist_ok=True)
            (output/'self-test-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            sys.exit(1)
    else:
        from speccompare.gui import main
        main()
