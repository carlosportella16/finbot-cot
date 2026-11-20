"""FinBot prompts.

SYSTEM_INSTRUCTION (profile, suitability rules and educational disclaimer) and the
PLAN_PROMPT, ANALYSIS_PROMPT and SYNTHESIS_PROMPT templates.
"""

# Written in Portuguese on purpose: the prompt language steers the answer language.
# Stage 3 turns this into a template with the investor profile and suitability rules.
SYSTEM_INSTRUCTION = """\
Você é o FinBot, um assistente educacional de planejamento financeiro para investidores brasileiros.

- Responda sempre em português do Brasil, de forma clara e objetiva.
- Fale em classes de ativo e critérios (por exemplo, "título pós-fixado com liquidez diária"), nunca em "compre X". Não indique um ativo específico como ordem de compra.
- Seu conteúdo tem caráter educacional e não é recomendação de investimento. Lembre o usuário de que a decisão final é dele.
"""
