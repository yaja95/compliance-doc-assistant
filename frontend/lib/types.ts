export interface UserRead {
  id: number;
  username: string;
  created_at: string;
}

export interface LoginResponse {
  token: string;
  user: UserRead;
}

export type DocumentStatus = "pending" | "chunked" | "embedded" | "failed";

export interface DocumentRead {
  id: number;
  filename: string;
  source_format: string;
  status: DocumentStatus;
  uploaded_at: string;
}

export interface ChunkRead {
  id: number;
  chunk_index: number;
  section_label: string | null;
  content: string;
  token_count: number;
}

export interface DocumentDetailRead extends DocumentRead {
  chunks: ChunkRead[];
}

export interface QuestionRead {
  id: number;
  document_id: number;
  question_text: string;
  created_at: string;
}

export interface AnswerCitationRead {
  chunk_id: number;
  chunk_index: number;
  content: string;
  relevance_score: number;
  rank: number;
}

export interface AnswerWithCitationsRead {
  id: number;
  question_id: number;
  answer_text: string;
  model_used: string;
  needs_review: boolean;
  confidence_reason: string | null;
  created_at: string;
  citations: AnswerCitationRead[];
}

export interface QuestionAnswerRead {
  question: QuestionRead;
  answer: AnswerWithCitationsRead;
}

export type ReviewFlagStatus = "pending" | "resolved" | "dismissed";

export interface ReviewFlagRead {
  id: number;
  answer_id: number;
  reason: string;
  status: ReviewFlagStatus;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
}
