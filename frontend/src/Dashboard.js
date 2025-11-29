import React, { useState, useEffect } from "react";
import StatementUpload from "./StatementUpload";
import { useNavigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import SmartGoalsButton from "./SmartGoals";
import ExpensePieChart from "./ExpensePieChart";

function Dashboard() {
  const navigate = useNavigate();
  const [smartGoalsOpen, setSmartGoalsOpen] = useState(false);
  const [insights, setInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("supabase_token");
    navigate("/login");
  };

  const fetchInsights = async () => {
    setLoadingInsights(true);
    try {
      const token = localStorage.getItem("supabase_token");
      const response = await fetch("http://localhost:8000/insights", {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      const data = await response.json();
      setInsights(data);
    } catch (error) {
      console.error("Error fetching insights:", error);
    } finally {
      setLoadingInsights(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <span>Finance Management</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <SmartGoalsButton onOpenChange={setSmartGoalsOpen} />
          <button className="upload-btn" onClick={handleLogout} style={{ cursor: "pointer", marginRight: 50 }}>
            Logout
          </button>
        </div>
      </header>

      <div className="dashboard">
        <div style={{ marginBottom: '40px' }}>
          <h2>Upload Statement</h2>
          <StatementUpload onUploadSuccess={fetchInsights} />
        </div>

        {!smartGoalsOpen && (
          <>
            {/* Financial Insights Section */}
            <div style={{ marginTop: '40px', background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
              <h2 style={{ marginBottom: '20px', color: '#333' }}>Financial Insights</h2>
              {loadingInsights ? (
                <p>Loading insights...</p>
              ) : insights ? (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '20px' }}>
                    <div style={{ padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
                      <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>Total Income</div>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4caf50' }}>
                        ${insights.total_income?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                    <div style={{ padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
                      <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>Total Expenses</div>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f44336' }}>
                        ${insights.total_expenses?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                    {insights.overspending && (
                      <div style={{ padding: '15px', background: '#ffebee', borderRadius: '8px', border: '2px solid #f44336' }}>
                        <div style={{ fontSize: '14px', color: '#d32f2f', fontWeight: 'bold' }}>⚠️ Over Budget</div>
                      </div>
                    )}
                  </div>
                  {insights.insights && insights.insights.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                      <h3 style={{ fontSize: '18px', marginBottom: '10px', color: '#555' }}>Key Insights</h3>
                      <ul style={{ listStyle: 'none', padding: 0 }}>
                        {insights.insights.map((insight, index) => (
                          <li key={index} style={{ padding: '8px 0', borderBottom: '1px solid #eee', color: '#666' }}>
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ color: '#999' }}>No insights available yet. Upload a statement to see your financial insights.</p>
              )}
            </div>

            {/* Expense Pie Chart Section */}
            <div style={{ marginTop: '40px', background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
              <ExpensePieChart />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Dashboard;

