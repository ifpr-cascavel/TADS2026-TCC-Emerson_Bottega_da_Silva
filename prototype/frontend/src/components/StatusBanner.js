import React from 'react';

// Small inline banner used for both error and informational feedback. Uses the
// ARIA live region role so screen readers announce validation problems.
const StatusBanner = ({ variant = 'info', children }) => {
  if (!children) {
    return null;
  }
  const isError = variant === 'error';
  return (
    <p
      className={`status-banner status-banner--${variant}`}
      role={isError ? 'alert' : 'status'}
    >
      {children}
    </p>
  );
};

export default StatusBanner;
