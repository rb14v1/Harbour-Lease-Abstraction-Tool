import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient } from "../api/client";
import type { Lease, LeaseQuery, LeaseTerm } from "../types";
import { Layout } from "../components/Layout";

export function LeaseDetailPage() {
  const { leaseId } = useParams();
  const [lease, setLease] = useState<Lease | null>(null);
  const [terms, setTerms] = useState<LeaseTerm[]>([]);
  const [queries, setQueries] = useState<LeaseQuery[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [leaseRes, termsRes, queriesRes] = await Promise.all([
      apiClient.get<Lease>(`/leases/${leaseId}/`),
      apiClient.get<LeaseTerm[]>(`/leases/${leaseId}/terms/`),
      apiClient.get<LeaseQuery[]>(`/leases/${leaseId}/queries/`),
    ]);
    setLease(leaseRes.data);
    setTerms(termsRes.data);
    setQueries(queriesRes.data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaseId]);

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAsking(true);
    try {
      await apiClient.post(`/leases/${leaseId}/queries/`, { question_text: question });
      setQuestion("");
      await load();
    } catch {
      setError("Could not get an answer. Has this lease been processed yet?");
    } finally {
      setAsking(false);
    }
  }

  if (!lease) return <Layout>Loading...</Layout>;

  return (
    <Layout>
      <p>
        <Link to={`/properties/${lease.property}`}>&larr; Back to leases</Link>
      </p>
      <h1>
        {lease.tenant_name} <span className={`status-badge status-${lease.status}`}>{lease.status}</span>
      </h1>
      <p className="muted">
        {lease.property_address} &middot; Landlord: {lease.landlord_name} &middot;{" "}
        {lease.start_date} &rarr; {lease.end_date}
      </p>

      <section className="card">
        <h2>Extracted lease terms</h2>
        {terms.length === 0 && <p className="muted">No terms extracted yet. Process the lease first.</p>}
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Value</th>
              <th>Source page</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((t) => (
              <tr key={t.id}>
                <td>{t.term_type}</td>
                <td>{t.extracted_value}</td>
                <td>{t.source_page}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Ask a question about this lease</h2>
        <form className="inline-form" onSubmit={handleAsk}>
          <input
            placeholder="e.g. What is the monthly rent?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
          <button type="submit" disabled={asking}>
            {asking ? "Asking..." : "Ask"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}

        <h3>History</h3>
        {queries.length === 0 && <p className="muted">No questions asked yet.</p>}
        <ul className="query-history">
          {queries.map((q) => (
            <li key={q.id}>
              <p className="question">
                <strong>Q:</strong> {q.question_text}
              </p>
              <p className="answer">
                <strong>A:</strong> {q.answer_text}
              </p>
              <p className="muted small">
                Asked by {q.asked_by_email} &middot; {new Date(q.created_at).toLocaleString()}{" "}
                &middot; {q.retrieved_chunk_ids.length} chunk(s) cited
              </p>
            </li>
          ))}
        </ul>
      </section>
    </Layout>
  );
}
