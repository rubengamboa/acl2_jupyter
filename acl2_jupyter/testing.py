
for line in SexpScanner("(foo bar (baz)) #|foo bar|#:foo bar\r\n; foo bar \r\n(1+ (- 3 4) ((+ 3 5) 7))"):
    print (line)