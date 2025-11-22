import React, { useRef } from "react";

export default function Dashboard() {
  const fileInputRef = useRef(null);

  const handleUploadClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    console.log("Uploaded file:", file);
    alert(`Uploaded: ${file.name}`);
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Welcome to your Financial Management System!</h1>

      <button style={styles.button} onClick={handleUploadClick}>
        Upload Bank Statement
      </button>

      <input
        type="file"
        accept=".csv, .xlsx, .xls"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
    </div>
  );
}

const styles = {
  container: {
    textAlign: "center",
    padding: "40px",
    fontFamily: "Arial",
  },
  header: {
    fontSize: "28px",
    marginBottom: "20px",
  },
  button: {
    padding: "12px 20px",
    fontSize: "16px",
    borderRadius: "8px",
    cursor: "pointer",
    backgroundColor: "#4CAF50",
    border: "none",
    color: "white",
  },
};
