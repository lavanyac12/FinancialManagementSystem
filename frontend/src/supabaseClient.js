import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.REACT_APP_SUPABASE_URL;
const SUPABASE_ANON = process.env.REACT_APP_SUPABASE_ANON;

if (!SUPABASE_URL || !SUPABASE_ANON) {
  console.warn('REACT_APP_SUPABASE_URL or REACT_APP_SUPABASE_ANON is not set.');
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);
