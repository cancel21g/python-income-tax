# 소득과 세금 변수 선언
income = 5500000  # 단위: 원
tax = 0  # 초기값

# if-else 문을 이용해 소득 수준에 따라 세율 적용
if income <= 2000000:
    tax = income * 0.10      # 저소득층 10%
    level = "저소득층"
elif income <= 5000000:
    tax = income * 0.25      # 중간소득층 25%
    level = "중간소득층"
else:
    tax = income * 0.50      # 고소득층 50%
    level = "고소득층"

# 결과 출력
print("소득 수준:", level)
print("소득 금액:", income, "원")
print("예상 세금:", int(tax), "원")
