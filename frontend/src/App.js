import React from "react";
import StatementUpload from "./StatementUpload";

function App() {
	return (
		<div style={{ maxWidth: 800, margin: "auto", padding: 20 }}>
			<h1>Financial Statement Parser</h1>
			<StatementUpload />
		</div>
	);
}

export default App;
