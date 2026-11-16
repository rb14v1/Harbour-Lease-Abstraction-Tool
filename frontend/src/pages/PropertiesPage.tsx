import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../api/client";
import type { Property } from "../types";
import { Layout } from "../components/Layout";

export function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [address, setAddress] = useState("");
  const [propertyType, setPropertyType] = useState("office");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const response = await apiClient.get<Property[]>("/properties/");
    setProperties(response.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiClient.post("/properties/", { address, property_type: propertyType });
      setAddress("");
      await load();
    } catch {
      setError("Could not create property.");
    }
  }

  return (
    <Layout>
      <h1>Properties</h1>
      <form className="inline-form" onSubmit={handleCreate}>
        <input
          placeholder="Address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          required
        />
        <select value={propertyType} onChange={(e) => setPropertyType(e.target.value)}>
          <option value="office">Office</option>
          <option value="retail">Retail</option>
          <option value="residential">Residential</option>
        </select>
        <button type="submit">Add property</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table className="data-table">
        <thead>
          <tr>
            <th>Address</th>
            <th>Type</th>
            <th>Leases</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {properties.map((p) => (
            <tr key={p.id}>
              <td>{p.address}</td>
              <td>{p.property_type}</td>
              <td>{p.lease_count}</td>
              <td>
                <Link to={`/properties/${p.id}`}>View leases</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  );
}
