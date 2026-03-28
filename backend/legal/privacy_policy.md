# Privacy Policy

**Effective Date:** March 28, 2026
**Version:** 1.0

## 1. Introduction

Text2trade ("we", "our", "the Platform") respects your privacy. This Privacy Policy explains how we collect, use, store, and protect your personal information when you use our Platform.

## 2. Data We Collect

### 2.1 Information You Provide
- **Account Data:** Email address, password (stored as bcrypt hash)
- **Profile Data:** Display name, phone number (optional), timezone, preferred instruments
- **Strategy Data:** Trading strategies you create, including indicators, conditions, and parameters
- **Backtest Data:** Backtest configurations, results, and performance metrics
- **Paper Trading Data:** Simulated trades, P&L records

### 2.2 Information Collected Automatically
- **Usage Analytics:** Pages visited, features used, time spent (anonymous, aggregated)
- **Error Reports:** Crash data, error messages, browser information (for debugging)
- **Request Logs:** API request metadata (endpoint, method, duration) with structured logging

### 2.3 Information We Do NOT Collect
- Broker account credentials (stored locally in your browser, never on our servers)
- Financial account numbers or bank details
- Government identification documents

## 3. How We Use Your Data

- **Account Management:** Authentication, authorization, and account recovery
- **Service Delivery:** Executing backtests, managing strategies, paper trading
- **Platform Improvement:** Aggregated analytics to improve features and fix bugs
- **Communication:** Password reset OTPs, system alerts (only via channels you enable)
- **Legal Compliance:** Maintaining records as required by applicable law

## 4. Data Storage and Security

- **Database:** MongoDB with encrypted connections
- **Passwords:** Hashed using bcrypt (12 rounds) — we never store plaintext passwords
- **Tokens:** JWT-based authentication with automatic expiry
- **Access:** Role-based access control; admin actions are logged

## 5. Data Sharing

**We do NOT share your personal data with third parties** except:
- When required by law, regulation, or legal process
- To protect our rights, property, or safety
- With your explicit consent

We do NOT sell your data. We do NOT use your data for advertising.

## 6. Third-Party Services

The Platform integrates with:
- **OpenAI (GPT):** For AI strategy generation — only strategy text is sent; no personal data
- **Resend:** For transactional emails (OTPs, alerts) — only your email address is shared

## 7. Cookies and Local Storage

- **Session Cookies:** Used for authentication. Essential for Platform functionality.
- **Local Storage:** Stores authentication tokens and UI preferences.
- **We do NOT use third-party tracking cookies.**
- **We do NOT use advertising cookies.**

## 8. Your Rights

You have the right to:
- **Access:** Request a copy of all data we hold about you (available via Profile > Export Data)
- **Rectification:** Update your personal information through your Profile
- **Deletion:** Request deletion of your account and data (Profile > Delete Account)
- **Data Portability:** Export your strategies, backtests, and trades in standard format
- **Withdraw Consent:** You may withdraw consent at any time by deleting your account

## 9. Data Retention

- **Active Accounts:** Data retained for the duration of your account
- **Deleted Accounts:** Data permanently deleted within 90 days of account deletion
- **Error Logs:** Automatically deleted after 90 days (TTL index)
- **Performance Logs:** Automatically deleted after 30 days (TTL index)
- **Consent Records:** Retained permanently for legal compliance

## 10. Children's Privacy

The Platform is not intended for users under 18 years of age. We do not knowingly collect data from minors.

## 11. International Users

The Platform is operated from India. If you access the Platform from outside India, you consent to the transfer of your data to India for processing.

## 12. Compliance

This policy is designed with consideration for:
- **Information Technology Act, 2000 (India)** and its amendments
- **SPDI Rules (2011)** for sensitive personal data
- **GDPR principles** (for users in the European Union)

## 13. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes by requiring re-acceptance within the Platform.

## 14. Contact

For privacy inquiries or to exercise your rights, contact us through the in-app feedback form.

---

*This document is a functional template and should be reviewed by a legal professional before production use.*
