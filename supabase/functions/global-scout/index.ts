import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_ANON_KEY') ?? ''
  )

  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) throw new Error('Missing Authorization header')
    
    const token = authHeader.replace('Bearer ', '')
    const { data: { user }, error: authError } = await supabase.auth.getUser(token)
    if (authError || !user) throw new Error('Unauthorized')

    // Fetch the industry from onboarding_responses (Step Index 2)
    const { data: onboardingData, error: onboardingError } = await supabase
      .from('onboarding_responses')
      .select('selection_tags')
      .eq('user_id', user.id)
      .eq('step_index', 2)
      .single()

    // selection_tags is an array, so we take the first choice
    const userNiche = onboardingData?.selection_tags?.[0] || 'Technology & Software'

    // Query only trends matching that specific industry name
    const { data: trends, error: dbError } = await supabase
      .from('trending_topics')
      .select('*')
      .eq('category', userNiche)
      .order('created_at', { ascending: false })
      .limit(10)

    if (dbError) throw dbError

    return new Response(
      JSON.stringify({ trendingTopics: trends || [] }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 200 }
    )

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 200
    })
  }
})