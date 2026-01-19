# Import convention
import streamlit as st

ani_list = ['짱구는못말려', '몬스터','릭앤모티','이종혁']
img_list = ['https://i.imgur.com/t2ewhfH.png', 
            'https://i.imgur.com/ECROFMC.png', 
            'https://i.imgur.com/MDKQoDc.jpg',
            'C:/Users/jonyeok/OneDrive/개인 자료/증명/이종혁_저용량.jpg']

# text_input을 활용해서 검색창을 만듭니다
# 이 검색창에 ani_list 안에 일부 단어가 일치하면
# img_list의 해당 이미지를 출력하는 로직을 만들어주세요

# if / for를 활용하면 될겁니다.
name = st.text_input('Enter image\'s name', key='name')
if name:
    for i, ani in enumerate(ani_list):
        if name in ani:
            st.image(img_list[i])