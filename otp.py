import random
def genotp():
    otp=''
    for i in range(2):
        otp=otp+random.choice([chr(i) for i in range(ord('A'),ord('Z')+1)])  #''+'B'==
        otp=otp+random.choice([chr(i) for i in range(ord('a'),ord('z')+1)])  #'B'+'c'==>'Bc'
        otp=otp+str(random.randint(0,9))
    return otp # Sn6Dm7