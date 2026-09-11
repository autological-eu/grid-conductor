export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      app_config: {
        Row: {
          key: string
          value: string
        }
        Insert: {
          key: string
          value: string
        }
        Update: {
          key?: string
          value?: string
        }
        Relationships: []
      }
      border_flow_hourly: {
        Row: {
          flow_mw: number
          ts: string
          zone_a: string
          zone_b: string
        }
        Insert: {
          flow_mw: number
          ts: string
          zone_a: string
          zone_b: string
        }
        Update: {
          flow_mw?: number
          ts?: string
          zone_a?: string
          zone_b?: string
        }
        Relationships: [
          {
            foreignKeyName: "border_flow_hourly_zone_a_fkey"
            columns: ["zone_a"]
            isOneToOne: false
            referencedRelation: "zones"
            referencedColumns: ["code"]
          },
          {
            foreignKeyName: "border_flow_hourly_zone_b_fkey"
            columns: ["zone_b"]
            isOneToOne: false
            referencedRelation: "zones"
            referencedColumns: ["code"]
          },
        ]
      }
      borders: {
        Row: {
          created_at: string
          id: string
          zone_a: string
          zone_b: string
        }
        Insert: {
          created_at?: string
          id?: string
          zone_a: string
          zone_b: string
        }
        Update: {
          created_at?: string
          id?: string
          zone_a?: string
          zone_b?: string
        }
        Relationships: [
          {
            foreignKeyName: "borders_zone_a_fkey"
            columns: ["zone_a"]
            isOneToOne: false
            referencedRelation: "zones"
            referencedColumns: ["code"]
          },
          {
            foreignKeyName: "borders_zone_b_fkey"
            columns: ["zone_b"]
            isOneToOne: false
            referencedRelation: "zones"
            referencedColumns: ["code"]
          },
        ]
      }
      em_cache: {
        Row: {
          cache_key: string
          fetched_at: string
          payload: Json
        }
        Insert: {
          cache_key: string
          fetched_at?: string
          payload: Json
        }
        Update: {
          cache_key?: string
          fetched_at?: string
          payload?: Json
        }
        Relationships: []
      }
      import_jobs: {
        Row: {
          created_at: string
          cursor_ts: string
          id: string
          last_error: string | null
          range_end: string
          range_start: string
          rows_imported: number
          signal: string
          status: string
          updated_at: string
          zone_code: string
        }
        Insert: {
          created_at?: string
          cursor_ts: string
          id?: string
          last_error?: string | null
          range_end: string
          range_start: string
          rows_imported?: number
          signal: string
          status?: string
          updated_at?: string
          zone_code: string
        }
        Update: {
          created_at?: string
          cursor_ts?: string
          id?: string
          last_error?: string | null
          range_end?: string
          range_start?: string
          rows_imported?: number
          signal?: string
          status?: string
          updated_at?: string
          zone_code?: string
        }
        Relationships: []
      }
      job_locks: {
        Row: {
          expires_at: string
          name: string
          pause_reason: string | null
          paused: boolean
          updated_at: string
        }
        Insert: {
          expires_at: string
          name: string
          pause_reason?: string | null
          paused?: boolean
          updated_at?: string
        }
        Update: {
          expires_at?: string
          name?: string
          pause_reason?: string | null
          paused?: boolean
          updated_at?: string
        }
        Relationships: []
      }
      model_validation: {
        Row: {
          created_at: string
          id: string
          metrics: Json
          passed: boolean
          period_end: string
          period_start: string
        }
        Insert: {
          created_at?: string
          id?: string
          metrics?: Json
          passed?: boolean
          period_end: string
          period_start: string
        }
        Update: {
          created_at?: string
          id?: string
          metrics?: Json
          passed?: boolean
          period_end?: string
          period_start?: string
        }
        Relationships: []
      }
      scenario_results: {
        Row: {
          base_metrics: Json
          climate_opportunity_ktco2: number
          created_at: string
          entsoe_indicators: Json
          hourly_summary: Json
          id: string
          market_opportunity_meur: number
          scenario_id: string
          scenario_metrics: Json
          status: string
        }
        Insert: {
          base_metrics?: Json
          climate_opportunity_ktco2?: number
          created_at?: string
          entsoe_indicators?: Json
          hourly_summary?: Json
          id?: string
          market_opportunity_meur?: number
          scenario_id: string
          scenario_metrics?: Json
          status?: string
        }
        Update: {
          base_metrics?: Json
          climate_opportunity_ktco2?: number
          created_at?: string
          entsoe_indicators?: Json
          hourly_summary?: Json
          id?: string
          market_opportunity_meur?: number
          scenario_id?: string
          scenario_metrics?: Json
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "scenario_results_scenario_id_fkey"
            columns: ["scenario_id"]
            isOneToOne: false
            referencedRelation: "scenarios"
            referencedColumns: ["id"]
          },
        ]
      }
      scenario_units: {
        Row: {
          border_zone_a: string | null
          border_zone_b: string | null
          capex_meur: number
          created_at: string
          delivery_months: number
          id: string
          params: Json
          scenario_id: string
          unit_type: string
          zone_code: string | null
        }
        Insert: {
          border_zone_a?: string | null
          border_zone_b?: string | null
          capex_meur?: number
          created_at?: string
          delivery_months?: number
          id?: string
          params?: Json
          scenario_id: string
          unit_type: string
          zone_code?: string | null
        }
        Update: {
          border_zone_a?: string | null
          border_zone_b?: string | null
          capex_meur?: number
          created_at?: string
          delivery_months?: number
          id?: string
          params?: Json
          scenario_id?: string
          unit_type?: string
          zone_code?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "scenario_units_scenario_id_fkey"
            columns: ["scenario_id"]
            isOneToOne: false
            referencedRelation: "scenarios"
            referencedColumns: ["id"]
          },
        ]
      }
      scenarios: {
        Row: {
          budget_meur: number | null
          created_at: string
          description: string | null
          id: string
          is_template: boolean
          name: string
          status: string
          target_id: string
          template_key: string | null
          updated_at: string
        }
        Insert: {
          budget_meur?: number | null
          created_at?: string
          description?: string | null
          id?: string
          is_template?: boolean
          name: string
          status?: string
          target_id: string
          template_key?: string | null
          updated_at?: string
        }
        Update: {
          budget_meur?: number | null
          created_at?: string
          description?: string | null
          id?: string
          is_template?: boolean
          name?: string
          status?: string
          target_id?: string
          template_key?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "scenarios_target_id_fkey"
            columns: ["target_id"]
            isOneToOne: false
            referencedRelation: "targets"
            referencedColumns: ["id"]
          },
        ]
      }
      targets: {
        Row: {
          climate_loss_ktco2: number
          computed_at: string
          congested_hours: number
          id: string
          market_loss_meur: number
          metrics: Json
          observed_capacity_mw: number | null
          period_end: string
          period_start: string
          total_hours: number
          zone_a: string
          zone_b: string
        }
        Insert: {
          climate_loss_ktco2?: number
          computed_at?: string
          congested_hours?: number
          id?: string
          market_loss_meur?: number
          metrics?: Json
          observed_capacity_mw?: number | null
          period_end: string
          period_start: string
          total_hours?: number
          zone_a: string
          zone_b: string
        }
        Update: {
          climate_loss_ktco2?: number
          computed_at?: string
          congested_hours?: number
          id?: string
          market_loss_meur?: number
          metrics?: Json
          observed_capacity_mw?: number | null
          period_end?: string
          period_start?: string
          total_hours?: number
          zone_a?: string
          zone_b?: string
        }
        Relationships: []
      }
      zone_hourly: {
        Row: {
          carbon_intensity: number | null
          load_mw: number | null
          mix: Json | null
          price_eur_mwh: number | null
          ts: string
          zone_code: string
        }
        Insert: {
          carbon_intensity?: number | null
          load_mw?: number | null
          mix?: Json | null
          price_eur_mwh?: number | null
          ts: string
          zone_code: string
        }
        Update: {
          carbon_intensity?: number | null
          load_mw?: number | null
          mix?: Json | null
          price_eur_mwh?: number | null
          ts?: string
          zone_code?: string
        }
        Relationships: [
          {
            foreignKeyName: "zone_hourly_zone_code_fkey"
            columns: ["zone_code"]
            isOneToOne: false
            referencedRelation: "zones"
            referencedColumns: ["code"]
          },
        ]
      }
      zones: {
        Row: {
          code: string
          country_code: string
          created_at: string
          lat: number
          lon: number
          name: string
        }
        Insert: {
          code: string
          country_code: string
          created_at?: string
          lat: number
          lon: number
          name: string
        }
        Update: {
          code?: string
          country_code?: string
          created_at?: string
          lat?: number
          lon?: number
          name?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      compute_targets: {
        Args: {
          congestion_ratio?: number
          min_spread?: number
          relief_share?: number
        }
        Returns: number
      }
      zone_summary: {
        Args: never
        Returns: {
          avg_carbon_intensity: number
          avg_price: number
          code: string
          country_code: string
          hours: number
          lat: number
          lon: number
          name: string
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
