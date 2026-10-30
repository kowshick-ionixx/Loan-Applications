from langchain.tools import tool
from policy_index import build_index

store = build_index()


@tool
def search_policy(query: str) -> str:
    """Search the bank's loan policy and return the matching policy text.
    Use this for any question about loan rules: eligibility, age, income,
    credit score, loan amounts, tenure, interest rates, processing fee,
    prepayment, late fees, required documents or disbursal.
    The returned text includes section numbers like 3.2 to cite.

    query: what to look for in the policy, e.g. "processing fee"
    """
    hits = store.similarity_search(query, k=3)
    return "\n\n".join(hit.page_content for hit in hits)
