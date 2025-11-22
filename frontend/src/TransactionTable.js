import React from "react";

function TransactionsTable({ transactions }) {
  if (!transactions.length) return null;
  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Description</th>
          <th>Amount</th>
          <th>Type</th>
          <th>Category</th>
        </tr>
      </thead>
      <tbody>
        {transactions.map((tx, idx) => (
          <tr key={idx}>
            <td>{tx.date}</td>
            <td>{tx.description}</td>
            <td>{tx.amount}</td>
            <td>{tx.transaction_type}</td>
            <td>{tx.category || "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default TransactionsTable;