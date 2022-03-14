retstr = ""
strfrmt = ""
for i in range(1163, -1, -1):
    retstr += "out[%d]," % i
    strfrmt += "%b,"
print(retstr)
print(strfrmt)

