# سياسة مراجعة الذكاء الاصطناعي (AI Review Policy)

الذكاء الاصطناعي في SecureGuide هو "مساعد تصنيف" وليس حكماً نهائياً. يجب الالتزام بالقواعد التالية عند استخدام AI لتصنيف العناصر المستوردة:

1. **الشفافية (Accountability):** يجب أن يُرجع نموذج AI الحقول التالية مع كل تصنيف:
   - `classification_confidence`: درجة الثقة من 0.0 إلى 1.0.
   - `classification_rationale`: تبرير نصي قصير لسبب اختيار هذا التصنيف.
   - `ai_review_status`: حالة المراجعة الآلية.
   - `requires_human_review`: هل يحتاج العنصر لمراجعة بشرية؟ (0 أو 1).
   - البدائل المرفوضة (إن وجدت).

2. **التدخل البشري الإلزامي:**
   - إذا كانت درجة الثقة (`classification_confidence`) **أقل من أو تساوي 0.70**:
     - يجب ضبط `requires_human_review = 1`.
     - يجب ضبط `ai_review_status = AIR-HUMAN-REVIEW`.
   - يمنع النشر التلقائي (Auto-publish) لأي عنصر ذي ثقة منخفضة.

3. **استقلال الجودة عن الحد الأدنى:** حالة المراجعة البشرية والثقة بعدان للجودة
   ولا يمنعان وحدهما اجتياز `MINIMUM_CATALOG_VALIDATION`. يجوز إدخال عنصر
   مكتمل بنيوياً إلى الكتالوج بحالة `APPROVED` للمراجعة مع إبقاء
   `AIR-HUMAN-REVIEW` و`requires_human_review=1` ظاهرين. ولا يجوز تحويله آلياً
   إلى `PUBLISHED` أو الادعاء باجتياز `STRICT_USACM_CONFORMANCE` قبل وجود الدليل.

3. **قيم `ai_review_status` المعتمدة (USACM):** `AIR-AUTO-ACCEPTED`، `AIR-HUMAN-REVIEW`، `AIR-HUMAN-APPROVED`، `AIR-HUMAN-REJECTED`.
