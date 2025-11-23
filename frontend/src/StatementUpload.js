import React, { useState } from "react";
import axios from "axios";
// We no longer render the full transactions list after upload — show a success message instead.

function StatementUpload() {
  const [file, setFile] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

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
      const API_ROOT = process.env.REACT_APP_API_URL || "http://localhost:8001";
      const res = await axios.post(`${API_ROOT}/parse-statement`, formData);
      // backend returns { message, supabase_response }
      // Do not display all transactions in the UI — show a short success message instead.
      setTransactions([]);
      setSuccess("Upload successful.");
      setError(err.response?.data?.detail || err.response?.data?.error || "Upload failed.");    
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
        <button type="submit">Upload</button>
      </form>
      {error && <div style={{ color: "red" }}>{error}</div>}
      {success && <div style={{ color: "green", marginTop: 8 }}>{success}</div>}
    </div>
  );
}

export default StatementUpload;