import React from "react";


export default function InfoItem({ label, value }) {
  return (
    <div className="flex justify-between border-b border-slate-800 py-2">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-300 font-medium">
        {value || "—"}
      </span>
    </div>
  );
}