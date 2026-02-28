# 在原有程式碼中新增測驗邏輯
def generate_quiz():
    """根據單字本生成測驗題"""
    if not st.session_state.vocab_list:
        return "單字本目前是空的，請先開始對話導入單字！"
    
    client = openai.OpenAI(api_key=api_key)
    vocab_context = str(st.session_state.vocab_list[-5:]) # 取最近5個單字
    
    prompt = f"""
    Based on these vocabulary words: {vocab_context}, generate 3 Multiple Choice Questions.
    Format: JSON {{"quizzes": [{{"question": "...", "options": ["A", "B", "C"], "answer": "A", "explanation": "..."}}]}}
    Include Chinese explanations.
    """
    res = client.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "system", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(res.choices.message.content)

# UI 部分新增測驗分頁
with st.expander("📝 挑戰模式：單字測驗"):
    if st.button("開始測驗"):
        quiz_data = generate_quiz()
        if isinstance(quiz_data, dict):
            for i, q in enumerate(quiz_data['quizzes']):
                st.write(f"**Q{i+1}: {q['question']}**")
                choice = st.radio(f"選擇答案 (Q{i+1})", q['options'], key=f"q_{i}")
                if st.button(f"檢查 Q{i+1} 答案"):
                    if choice == q['answer']:
                        st.success(f"正確！{q['explanation']}")
                    else:
                        st.error(f"寫錯囉，正確答案是 {q['answer']}。{q['explanation']}")
