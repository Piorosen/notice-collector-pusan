export type DashboardSummary = {
  today_notice_count: number;
  today_meals: { breakfast?: string | null; lunch?: string | null; dinner?: string | null };
  today_meals_by_cafeteria?: Array<{
    cafeteria_key: string;
    cafeteria_name: string;
    breakfast?: string | null;
    lunch?: string | null;
    dinner?: string | null;
  }>;
  top_notices: Array<{ id: number; title: string; source: string; published_at?: string | null; has_attachment?: boolean }>;
  last_sync: {
    job_id?: number | null;
    status?: string;
    updated_at?: string | null;
    message?: string | null;
    current_source?: string | null;
    stage_current?: string | null;
    progress_total_pages?: number;
    progress_done_pages?: number;
    stage_total?: number;
    stage_done?: number;
  };
  source_stats: Array<{ source: string; source_display_name?: string; count: number }>;
};
