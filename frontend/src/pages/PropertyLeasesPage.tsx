import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient } from "../api/client";
import type { Lease } from "../types";
import { Layout } from "../components/Layout";
import { useAuth } from "../context/AuthContext";

export function PropertyLeasesPage() {
  const { propertyId } = useParams();
  const { user } = useAuth();
  const [leases, setLeases] = useState<Lease[]>([]);
  const [tenantName, setTenantName] = useState("");
  const [landlordName, setLandlordName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    const response = await apiClient.get<Lease[]>("/leases/");
    setLeases(response.data.filter((l) => String(l.property) === propertyId));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyId]);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("Choose a lease document file.");
      return;
    }
    const formData = new FormData();
    formData.append("property", propertyId as string);
    formData.append("tenant_name", tenantName);
    formData.append("landlord_name", landlordName);
    formData.append("start_date", startDate);
    formData.append("end_date", endDate);
    formData.append("file", file);

    try {
      await apiClient.post("/leases/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTenantName("");
      setLandlordName("");
      setStartDate("");
      setEndDate("");
      setFile(null);
      await load();
    } catch {
      setError("Could not upload lease. Check all fields are filled in.");
    }
  }

  async function handleProcess(leaseId: number) {
    setBusyId(leaseId);
    try {
      await apiClient.post(`/leases/${leaseId}/process/`);
      await load();
    } catch {
      setError("Could not process lease.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(leaseId: number) {
    try {
      await apiClient.delete(`/leases/${leaseId}/`);
      await load();
    } catch {
      setError("Could not delete lease (admin only).");
    }
  }

  return (
    <Layout>
      <p>
        <Link to="/properties">&larr; All properties</Link>
      </p>
      <h1>Leases</h1>

      <form className="card upload-form" onSubmit={handleUpload}>
        <h2>Upload a lease document</h2>
        <div className="form-grid">
          <label>
            Tenant name
            <input value={tenantName} onChange={(e) => setTenantName(e.target.value)} required />
          </label>
          <label>
            Landlord name
            <input
              value={landlordName}
              onChange={(e) => setLandlordName(e.target.value)}
              required
            />
          </label>
          <label>
            Start date
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </label>
          <label>
            End date
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </label>
          <label>
            Document (.txt)
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
        </div>
        <button type="submit">Upload lease</button>
      </form>
      {error && <p className="error">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Tenant</th>
            <th>Landlord</th>
            <th>Term</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {leases.map((lease) => (
            <tr key={lease.id}>
              <td>{lease.tenant_name}</td>
              <td>{lease.landlord_name}</td>
              <td>
                {lease.start_date} &rarr; {lease.end_date}
              </td>
              <td>
                <span className={`status-badge status-${lease.status}`}>{lease.status}</span>
              </td>
              <td className="actions">
                <Link to={`/leases/${lease.id}`}>Open</Link>
                {lease.status !== "processed" && (
                  <button
                    className="link-button"
                    onClick={() => handleProcess(lease.id)}
                    disabled={busyId === lease.id}
                  >
                    {busyId === lease.id ? "Processing..." : "Process"}
                  </button>
                )}
                {user?.role === "admin" && (
                  <button className="link-button danger" onClick={() => handleDelete(lease.id)}>
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  );
}
