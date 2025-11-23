import React, { useState } from "react";
import axios from "axios";
import TransactionTable from "./TransactionTable";

function StatementUpload() {
  const [file, setFile] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleFileChange = (e) => setFile(e.target.files[0]);
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return setError("Select a file.");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const token = localStorage.getItem('supabase_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post("http://localhost:8000/parse-statement", formData, { headers });
      // Supabase batch insert returns data inside supabase_response.data
      const inserted = res.data?.supabase_response?.data ?? [];
      setTransactions(inserted);
      setSuccess(res.data?.message || `Inserted ${inserted.length} transactions.`);
      setError("");
    } catch (err) {
      // Prefer detailed server error if available
      const serverData = err.response?.data;
      const detail = serverData?.detail || serverData?.error || serverData?.message || serverData || err.message;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      setSuccess("");
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
        <button type="submit">Upload</button>
      </form>
      {error && <div style={{ color: "#d32f2f", marginTop: 12 }}>{error}</div>}
      {success && <div style={{ color: "#2e7d32", marginTop: 12 }}>{success}</div>}
      <TransactionTable transactions={transactions} />
    </div>
  );
}

export default StatementUpload;