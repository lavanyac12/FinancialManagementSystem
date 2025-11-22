import React, { useState } from "react";
import "./App.css";

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setUploadedFiles((prev) => [...prev, file]);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <span>Finance Management</span>
      </header>

      {/* Dashboard */}
      <div className="dashboard">

        <label className="upload-btn">
          Upload Bank Statement
          <input
            type="file"
            accept=".csv, .xlsx, .xls"
            onChange={handleFileUpload}
            className="hidden-input"
          />
        </label>

        {uploadedFiles.length > 0 && (
          <div className="uploaded-files">
            <h2>Uploaded Files:</h2>
            <ul>
              {uploadedFiles.map((file, index) => (
                <li key={index}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
