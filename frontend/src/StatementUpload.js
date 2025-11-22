import React, { useState } from "react";
import axios from "axios";
import TransactionTable from "./TransactionTable";

function StatementUpload() {
  const [file, setFile] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState("");

  const handleFileChange = (e) => setFile(e.target.files[0]);
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return setError("Select a file.");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post("http://localhost:8000/parse-statement", formData);
      setTransactions(res.data);
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
        <button type="submit">Upload</button>
      </form>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <TransactionTable transactions={transactions} />
    </div>
  );
}

export default StatementUpload;