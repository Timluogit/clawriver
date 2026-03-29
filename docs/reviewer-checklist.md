# Reviewer Checklist - 质检清单

## Overview

This checklist is used by specialist-reviewer to review code changes, features, and deployments before they go live. It ensures quality, security, and compliance standards are met.

## Code Review

### Functionality
- [ ] Feature meets requirements and specifications
- [ ] Edge cases are handled properly
- [ ] Error handling is comprehensive
- [ ] User experience is consistent with design
- [ ] Performance is acceptable (load testing if needed)

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Code is readable and maintainable
- [ ] Variable/function names are descriptive
- [ ] Complex logic has comments
- [ ] No dead or commented-out code
- [ ] No hardcoded values (use config/env variables)

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests work correctly
- [ ] Test coverage meets project standards (>80%)
- [ ] All tests pass locally and in CI
- [ ] Manual testing completed (if applicable)

### Documentation
- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Comments explain complex logic
- [ ] Migration guide provided (for breaking changes)

---

## Security Review

### Authentication & Authorization
- [ ] Authentication is properly implemented
- [ ] Authorization checks are in place
- [ ] Session management is secure
- [ ] Password reset flow is secure
- [ ] Multi-factor authentication (if required)

### Data Protection
- [ ] Sensitive data is encrypted at rest
- [ ] Sensitive data is encrypted in transit
- [ ] PII is properly handled and protected
- [ ] Logs do not contain sensitive information
- [ ] Input validation is implemented

### API Security
- [ ] API rate limiting is implemented
- [ ] API authentication is required
- [ ] API responses are properly paginated
- [ ] API error messages do not leak information
- [ ] API versioning is handled

---

## Security Compliance Check (NEW)

### Frontend Security
- [ ] **No API Key / Secret hardcoded in JS/HTML**
  - Check all `.js`, `.jsx`, `.ts`, `.tsx`, `.html` files
  - Verify no hardcoded credentials (API keys, tokens, passwords)
  - Use environment variables or backend proxy instead
- [ ] **No sensitive data in localStorage/sessionStorage**
- [ ] **Content Security Policy (CSP) headers configured**
- [ ] **XSS protection measures in place**

### Data Attribution
- [ ] **Third-party data sources have correct license/attribution**
  - OpenAlex: CC BY 4.0 attribution on UI
  - Other APIs: Check license requirements
  - Display attribution near data source usage
- [ ] **Copyright notices are displayed**
- [ ] **License file is included in repository**

### Privacy Compliance
- [ ] **Privacy Policy page exists and is accessible**
  - URL: `/privacy` or similar
  - Link in footer or navigation
  - Content covers: data collection, usage, sharing, user rights
- [ ] **Cookie consent banner (if using cookies)**
- [ ] **User data flow is documented**
- [ ] **Data retention policy is stated**

### API Security
- [ ] **Rate limiting implemented on public endpoints**
  - Per-user rate limits
  - Per-IP rate limits
  - Appropriate limits (e.g., 100 req/min)
- [ ] **Authentication on sensitive endpoints**
  - Admin endpoints require auth
  - User data access requires auth
  - Proper JWT/session validation
- [ ] **API input validation**
  - SQL injection prevention
  - Command injection prevention
  - File upload restrictions

### Content Compliance
- [ ] **No illegal content stored or distributed**
- [ ] **Content moderation in place (UGC)**
- [ ] **Fair use for quotations and excerpts**
- [ ] **Terms of Service page exists**

### User Disclosure
- [ ] **User consent for data collection**
- [ ] **Third-party API usage disclosed in UI**
  - "Search queries are sent to OpenAlex API"
  - Similar disclosure for other third-party services
- [ ] **Data sharing transparency**
- [ ] **Opt-out options available (if applicable)**

---

## Deployment Review

### Pre-Deployment
- [ ] Feature flags are configured (if using)
- [ ] Database migrations are tested
- [ ] Environment variables are set
- [ ] Secrets are properly configured
- [ ] Backup plan is in place

### Monitoring & Logging
- [ ] Logging is comprehensive
- [ ] Error tracking is configured (Sentry, etc.)
- [ ] Performance monitoring is set up
- [ ] Alert rules are configured
- [ ] Dashboard is updated

### Rollback Plan
- [ ] Rollback procedure is documented
- [ ] Database rollback is tested (if needed)
- [ ] Rollback time is acceptable
- [ ] Stakeholders are notified of rollback plan

---

## User Acceptance Testing (UAT)

### Functional Testing
- [ ] Main user flows work correctly
- [ ] UI matches design specifications
- [ ] Mobile responsiveness verified
- [ ] Accessibility standards met (WCAG 2.1)
- [ ] Cross-browser compatibility tested

### Performance Testing
- [ ] Page load time acceptable (<3s)
- [ ] API response time acceptable
- [ ] System handles expected load
- [ ] No memory leaks detected
- [ ] Database queries optimized

---

## Sign-off

### Reviewer
- **Reviewer Name:** ___________________
- **Review Date:** ___________________
- **Overall Assessment:** [ ] Approved [ ] Needs Revisions [ ] Rejected
- **Blockers:** ___________________

### Approver
- **Approver Name:** ___________________
- **Approval Date:** ___________________
- **Approved for Deployment:** [ ] Yes [ ] No
- **Notes:** ___________________

---

## Common Issues Found in Reviews

### P0 - Critical
1. **Hardcoded API Keys in Frontend** - Move to backend proxy or env variables
2. **SQL Injection Vulnerabilities** - Use parameterized queries
3. **Missing Authentication** - Add auth to sensitive endpoints
4. **No Rate Limiting** - Implement rate limiting on public APIs

### P1 - High
1. **Missing Privacy Policy** - Create and link to privacy policy
2. **No Data Attribution** - Add license attribution for third-party data
3. **Poor Error Handling** - Improve error messages and handling
4. **Performance Issues** - Optimize slow queries and API calls

### P2 - Medium
1. **Missing Unit Tests** - Add tests for new functionality
2. **Documentation Gaps** - Update README and API docs
3. **UI/UX Issues** - Fix inconsistent design
4. **Code Style Violations** - Follow style guidelines

---

## References

- [Security Best Practices](./compliance-checklist.md)
- [Coding Standards](../developer-guide-team.md)
- [Deployment Checklist](./deploy-checklist.md)
- [GDPR Compliance](./compliance-checklist.md#gdpr)

---

*Last updated: 2026-03-30*
