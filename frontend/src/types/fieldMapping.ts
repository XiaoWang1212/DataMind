/**
 * 後端只產生前三種。
 * SKIPPED（我的資料沒有這個變數）與 CONFIRMED（使用者看過了、沒問題）
 * 是前端專屬，後端永遠不會回傳也不會收到。
 */
export type MappingStatus =
  | 'AUTO_MATCHED'
  | 'NEEDS_REVIEW'
  | 'UNMATCHED'
  | 'SKIPPED'
  | 'CONFIRMED'

/** 論文擷取出來的變數。is_target 的那一筆一律視為必要。 */
export interface PaperVariable {
  name: string
  type: string
  required?: boolean
  is_target?: boolean
}

/** 使用者資料表的欄位，樣本值取前 5 筆。 */
export interface UserColumn {
  name: string
  sample_values: string[]
}

export interface MappingItem {
  paper_variable: string
  required_type: string
  matched_user_column: string | null
  confidence_score: number
  status: MappingStatus
  sample_values: string[]
  candidate_columns: string[]
}

export interface MappingState {
  total_required: number
  matched_count: number
  mapping_status: MappingItem[]
}

/** chat_refine 回傳的單筆變更。 */
export interface MappingAction {
  paper_variable: string
  matched_user_column: string | null
  status: MappingStatus
  confidence_score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
