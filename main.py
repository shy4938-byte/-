import sys
if __name__ == '__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        from speccompare.verification import verify_suite
        verify_suite(sys.argv[2])
    elif len(sys.argv)==4 and sys.argv[1]=='--verify-package':
        from speccompare.verification import verify
        verify(sys.argv[2],sys.argv[3])
    else:
        from speccompare.gui import main
        main()
