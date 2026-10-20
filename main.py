import sys
if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--verify-package':
        from speccompare.verification import verify
        verify(sys.argv[2], sys.argv[3])
    else:
        from speccompare.gui import main
        main()
