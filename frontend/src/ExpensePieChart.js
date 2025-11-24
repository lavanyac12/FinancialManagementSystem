import React, { useState, useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { supabase } from "./supabaseClient";
import axios from "axios";

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#ff7c7c'];

function ExpensePieChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchExpenseData();
  }, []);

  const fetchExpenseData = async () => {
    try {
      setLoading(true);
      setError("");

      const token = localStorage.getItem("supabase_token");
      if (!token) {
        setError("Not authenticated");
        setLoading(false);
        return;
      }

      // Fetch categories from backend API (bypasses RLS)
      const categoriesResponse = await axios.get(
        "http://localhost:8000/categories",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const categories = categoriesResponse.data.categories || [];
      console.log("Fetched categories from backend:", categories);
      console.log("Number of categories:", categories.length);

      // Fetch transactions from Supabase
      const { data: transactions, error: txError } = await supabase
        .from("transactions")
        .select("amount, transaction_type, category_id");

      if (txError) {
        console.error("Error fetching transactions:", txError);
        setError(`Failed to load expense data: ${txError.message}`);
        setLoading(false);
        return;
      }

      if (!transactions || transactions.length === 0) {
        setData([]);
        setLoading(false);
        return;
      }

      console.log("Fetched transactions:", transactions.slice(0, 5)); // Log first 5 transactions
      console.log("Sample transactions with all fields:", transactions.slice(0, 10).map(t => ({ 
        amount: t.amount, 
        type: t.transaction_type, 
        cat: t.category_id,
        desc: t.description 
      })));

      // Create category lookup map
      const categoryMap = {};
      categories.forEach(cat => {
        categoryMap[cat.category_id] = cat.category_name;
      });

      console.log("Category map:", categoryMap);

      // Filter only expenses (negative amounts OR debit transactions)
      // Only include transactions where transaction_type is exactly 'Debit' (case-insensitive)
      const expenses = transactions.filter((tx) => {
        return (
          tx.transaction_type &&
          tx.transaction_type.trim().toLowerCase() === 'debit'
        );
      });

      console.log(`Total transactions: ${transactions.length}, Debit Expenses: ${expenses.length}`);
      console.log("Sample expense:", expenses[0]);

      // Group by category
      const categoryTotals = {};
      expenses.forEach((tx) => {
        const categoryName = categoryMap[tx.category_id] || "Uncategorized";
        const amount = Math.abs(tx.amount); // Use absolute value for display
        
        console.log(`Transaction: ${tx.category_id} -> ${categoryName}, Amount: ${amount}`);
        
        if (categoryTotals[categoryName]) {
          categoryTotals[categoryName] += amount;
        } else {
          categoryTotals[categoryName] = amount;
        }
      });

      // Convert to array format for Recharts
      const chartData = Object.entries(categoryTotals).map(([name, value]) => ({
        name,
        value: parseFloat(value.toFixed(2))
      }));

      // Sort by value descending
      chartData.sort((a, b) => b.value - a.value);

      console.log("Chart data:", chartData);
      setData(chartData);
      setLoading(false);
    } catch (err) {
      console.error("Exception fetching expense data:", err);
      setError(`An error occurred: ${err.message}`);
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ 
          background: 'white', 
          padding: '10px', 
          border: '1px solid #ccc',
          borderRadius: '4px'
        }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>{payload[0].name}</p>
          <p style={{ margin: 0, color: payload[0].fill }}>
            ${payload[0].value.toFixed(2)}
          </p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '20px' }}>Loading expense data...</div>;
  }

  if (error) {
    return <div style={{ textAlign: 'center', padding: '20px', color: 'red' }}>{error}</div>;
  }

  if (data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '20px' }}>
        No expense data available. Upload transactions to see the breakdown.
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 400 }}>
      <h3 style={{ textAlign: 'center', marginBottom: '20px' }}>Expenses by Category</h3>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
            outerRadius={120}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
      <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '14px', color: '#666' }}>
        Total Expenses: ${data.reduce((sum, item) => sum + item.value, 0).toFixed(2)}
      </div>
    </div>
  );
}

export default ExpensePieChart;
