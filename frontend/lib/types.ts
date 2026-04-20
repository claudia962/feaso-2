/**
 * Shape mirrors `app/models/schemas.py` on the backend. Kept intentionally
 * loose — backend is the source of truth; extra fields are tolerated.
 */

export type Recommendation =
  | 'strong_buy'
  | 'buy'
  | 'hold'
  | 'avoid'
  | 'strong_avoid';

export interface AnalysisRequest {
  address: string;
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  purchase_price: number;
  estimated_renovation?: number;
  down_payment_pct?: number;
  mortgage_rate_pct?: number;
  mortgage_term_years?: number;
  created_by?: string;
}

export interface NeighborhoodResponse {
  walk_score?: number | null;
  transit_score?: number | null;
  bike_score?: number | null;
  nearest_airport_km?: number | null;
  nearest_airport_name?: string | null;
  nearest_beach_km?: number | null;
  nearest_downtown_km?: number | null;
  restaurants_within_1km?: number | null;
  grocery_within_1km?: number | null;
  neighborhood_score?: number | null;
  best_for?: string[];
}

export interface CompResponse {
  comp_listing_id?: string | null;
  comp_name?: string | null;
  distance_km?: number | null;
  bedrooms?: number | null;
  annual_revenue?: number | null;
  avg_adr?: number | null;
  occupancy_rate?: number | null;
  similarity_score?: number | null;
  data_source?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface FinancialResponse {
  projection_type: string;
  year1_gross_revenue?: number | null;
  noi?: number | null;
  cap_rate?: number | null;
  cash_on_cash_return?: number | null;
  break_even_occupancy?: number | null;
  monthly_projections?: Array<{
    month: string;
    adr: number;
    occupancy: number;
    revenue: number;
    occupied_nights: number;
  }>;
  annual_expenses?: Record<string, number>;
  mc_revenue_p10?: number | null;
  mc_revenue_p25?: number | null;
  mc_revenue_p50?: number | null;
  mc_revenue_p75?: number | null;
  mc_revenue_p90?: number | null;
}

export interface StressResult {
  scenario_name: string;
  scenario_type: string;
  revenue_impact_pct?: number | null;
  still_profitable?: boolean | null;
  adaptation_strategy?: string | null;
}

export interface AnalysisResponse {
  id: string;
  status: string;
  address: string;
  created_at: string;
  overall_feasibility_score?: number | null;
  risk_score?: number | null;
  recommendation?: Recommendation | null;
  recommendation_reasoning?: string | null;
  neighborhood?: NeighborhoodResponse | null;
  comps?: CompResponse[];
  financials?: FinancialResponse | null;
  all_projections?: FinancialResponse[];
  stress_results?: StressResult[];
  steps_complete?: string[];
  metadata?: {
    monte_carlo?: {
      histogram_bins?: number[];
      histogram_counts?: number[];
      noi_p10?: number;
      noi_p50?: number;
      noi_p90?: number;
      coc_p50?: number;
      probability_of_loss?: number;
    };
    score_breakdown?: Record<string, number>;
    comp_summary?: Record<string, unknown>;
    event_impact?: {
      events_within_radius?: number;
      total_event_nights?: number;
      annual_revenue_contribution?: number;
      comparison?: string;
    };
  };
}

export interface CompListResponse {
  feasibility_id: string;
  count: number;
  comps: CompResponse[];
}

export interface RegulationResponse {
  feasibility_id: string;
  municipality: string;
  str_allowed: boolean;
  permit_required: boolean;
  max_nights_per_year?: number | null;
  regulation_risk_score?: number | null;
  last_verified?: string | null;
  notes?: string | null;
}

export interface PortfolioResponse {
  feasibility_id: string;
  existing_property_count: number;
  overall_score?: number | null;
  recommendation: string;
}
