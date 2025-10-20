# streamlit_app.py
import streamlit as st

st.title("간단 소득세 계산기")

income = st.number_input("소득(원)", min_value=0, step=10000, value=5_500_000)

# 기존 로직: 구간에 따라 단일세율 적용
if income <= 2_000_000:
    tax = income * 0.10
    level = "저소득층 (10%)"
elif income <= 5_000_000:
    tax = income * 0.25
    level = "중간소득층 (25%)"
else:
    tax = income * 0.50
    level = "고소득층 (50%)"

st.write(f"**소득 수준:** {level}")
st.metric("예상 세금", f"{int(tax):,} 원")
