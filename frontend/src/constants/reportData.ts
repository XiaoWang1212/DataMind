import type { JSONContent } from '@tiptap/core'

export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
}

export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
}

export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citations: [
    {
      id: 'cite-1',
      title: 'Benchmarking Machine Learning Algorithms for Telecom Churn Prediction',
      authors: 'Chen, W., & Smith, J.',
      journal: 'International Journal of Data Science, 12(4)',
      year: 2023,
      snippet:
        '“...Our empirical comparison demonstrates that gradient boosting frameworks (specifically XGBoost) consistently outperform SVM. Their superiority is attributed to their robustness in handling mixed data types and modeling non-linear interactions...”',
    },
    {
      id: 'cite-2',
      title: 'Switching Costs and Customer Loyalty in Subscription-Based Markets',
      authors: 'Kumar, A., & Lee, D.',
      journal: 'Journal of Marketing Analytics, 8(2)',
      year: 2024,
      snippet:
        '“...Customers under long-term contracts exhibit significantly lower churn propensity, as contractual switching costs reinforce retention even when short-term satisfaction fluctuates...”',
    },
  ],
  content: {
    type: 'doc',
    content: [
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.1 模型效能評估 (Model Performance Evaluation)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '本研究採用分層十折交叉驗證 (Stratified 10-Fold Cross-Validation) 對三種異質模型進行了嚴謹的基準測試。實驗結果顯示,XGBoost 模型在各項關鍵指標上均優於隨機森林 (Random Forest) 與支持向量機 (SVM),其準確率 (Accuracy) 達到 94.2%,F1-Score 為 0.92。相較之下,SVM 在處理類別不平衡數據時表現較弱,Recall 僅為 0.76。這項結果與近期文獻一致,指出梯度提升決策樹 (GBDT) 演算法由於具備處理特徵間複雜非線性交互作用的能力,在結構化表格數據 (Tabular Data) 的分類任務中,通常能提供比傳統統計模型更穩健的預測能力',
            marks: [{ type: 'citation', attrs: { citationId: 'cite-1' } }],
          },
          { type: 'text', text: '。因此,本系統最終選擇 XGBoost 作為部署至生產環境的最佳模型。' },
        ],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.2 關鍵特徵影響因子分析 (Analysis of Key Determinants)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '進一步透過 SHAP (SHapley Additive exPlanations) 值解析模型的決策邏輯,我們發現「合約類型 (Contract Type)」是預測客戶流失的最顯著特徵。SHAP Summary Plot 顯示,合約期限越短,SHAP 值越高,代表流失風險越大。數據顯示,採「按月付費 (Month-to-month)」合約的客戶,其基礎流失機率比簽訂「兩年合約」的長期客戶高出 45%,這反映了合約轉換成本 (Switching Cost) 會顯著降低客戶的忠誠度',
            marks: [{ type: 'citation', attrs: { citationId: 'cite-2' } }],
          },
          { type: 'text', text: '。這表明,電信營運商應將行銷資源集中於引導月租客戶升級至年約方案,而非僅依賴價格補貼。' },
        ],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.3 服務類型與市場競爭 (Service Type and Market Competition)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '除了合約結構,「光纖網路服務 (Fiber Optic)」的使用者群體也呈現出異常高的流失傾向。雖然光纖用戶通常貢獻較高的 ARPU (每用戶平均收入),但模型預測顯示其流失風險反而是 DSL 用戶的 1.5 倍。針對此現象,可能的解釋包括光纖市場競爭激烈、價格敏感度高,以及用戶對高價服務的品質期望更為嚴苛,值得後續研究進一步驗證。',
          },
        ],
      },
    ],
  },
}
