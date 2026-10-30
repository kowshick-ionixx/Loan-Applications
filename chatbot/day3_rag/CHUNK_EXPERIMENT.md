# Chunk-size experiment

1. I ran all 10 questions at `chunk_size=300` (8 chunks) and `chunk_size=80` (32 chunks), fetching the top 3 chunks each time.
2. Q5 broke at 80: rule 4.3 was cut in half, the "last 2 years of ITR for self-employed" part never came back, so the model answered with the salaried proof and no section. That is a retrieval problem.
3. Q7 at 80 came back cut off ("...after documents are") because "verified" landed in another chunk; Q2 only survived because the overlap repeated "and 699 are referred to a credit officer".
4. Q3 changed the other way: at 80 the model worked out Rs 9,000, at 300 it only said 1.5 percent. Rule 3.2 was retrieved both times, so that difference is the model, not the retriever.
5. Q1, Q6, Q8, Q9 and Q10 stayed correct at both sizes because short rules fit in 80 characters. I would keep 300: every rule arrives whole with its number, and Q4's missing 2% charge (wrong at both sizes) is a prompt fix, not a chunking one.
