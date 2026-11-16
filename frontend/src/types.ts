export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: "property_manager" | "admin";
  date_joined: string;
}

export interface Property {
  id: number;
  address: string;
  property_type: "office" | "retail" | "residential";
  created_at: string;
  lease_count: number;
}

export interface Lease {
  id: number;
  property: number;
  property_address: string;
  tenant_name: string;
  landlord_name: string;
  blob_path: string;
  start_date: string;
  end_date: string;
  status: "uploaded" | "processing" | "processed";
  created_at: string;
  updated_at: string;
}

export interface LeaseTerm {
  id: number;
  lease: number;
  term_type: "rent" | "renewal" | "termination" | "maintenance";
  extracted_value: string;
  source_page: number;
}

export interface LeaseQuery {
  id: number;
  lease: number;
  asked_by: number;
  asked_by_email: string;
  question_text: string;
  answer_text: string;
  retrieved_chunk_ids: string[];
  created_at: string;
}
