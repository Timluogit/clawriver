# Deploy Checklist - 部署清单

## Overview

This checklist is used to ensure safe and compliant deployments to production. All items must be checked before merging to main branch or deploying to production.

## Pre-Deployment Checks

### Code Quality
- [ ] All tests pass in CI/CD pipeline
- [ ] Code review approved by specialist-reviewer
- [ ] No critical or high-severity security vulnerabilities
- [ ] No TODOs or FIXMEs in production code
- [ ] No debug or console.log statements in production code
- [ ] Code coverage threshold met (>80%)

### Feature Readiness
- [ ] Feature is complete and tested
- [ ] Documentation is updated (README, API docs)
- [ ] User-facing changes are communicated
- [ ] Backward compatibility maintained (or migration plan exists)
- [ ] Feature flags configured (if applicable)

### Database
- [ ] Database migrations tested in staging
- [ ] Migration rollback plan documented
- [ ] Data backups verified before migration
- [ ] No destructive migrations without explicit approval
- [ ] Indexes are optimized for new queries

---

## Security Compliance Check (NEW)

### Secrets & Credentials
- [ ] **No hardcoded secrets in code**
  - Check all files for API keys, passwords, tokens
  - Use environment variables or secret management
  - Verify secrets are not in git history
- [ ] **Environment variables are configured**
  - Production secrets are in .env.production
  - Secrets are rotated regularly
  - Access to secrets is restricted
- [ ] **Secret scanning completed**
  - Run `git-secrets` or similar tool
  - No secrets in recent commits

### Frontend Security
- [ ] **No API keys in frontend bundle**
  - Verify webpack/vite build output
  - Check browser DevTools for exposed credentials
  - Use backend proxy for API calls
- [ ] **Content Security Policy (CSP) configured**
  - CSP header is set on all pages
  - No unsafe-inline or unsafe-eval
  - Report-only mode tested first
- [ ] **Security headers configured**
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY or SAMEORIGIN
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security: max-age=31536000
- [ ] **Subresource Integrity (SRI) for CDN resources**

### Data Protection
- [ ] **Encryption in transit**
  - HTTPS is enforced (redirect HTTP to HTTPS)
  - SSL/TLS certificate is valid
  - TLS 1.2 or higher only
- [ ] **Encryption at rest**
  - Database encryption enabled
  - Disk encryption on servers
  - Backup files encrypted
- [ ] **PII protection**
  - Sensitive data is masked in logs
  - PII access is audited
  - Data retention policy enforced

### API Security
- [ ] **Rate limiting configured**
  - Public API endpoints have rate limits
  - DDoS protection is enabled
  - Rate limit headers are visible (X-RateLimit-*)
- [ ] **Authentication and authorization**
  - All sensitive endpoints require auth
  - JWT tokens are properly validated
  - Session management is secure
- [ ] **API security headers**
  - CORS properly configured
  - API versioning is enforced
  - Authentication error messages don't leak info

### Privacy Compliance
- [ ] **Privacy Policy page is live**
  - URL is accessible: /privacy
  - Page is linked in footer/nav
  - Content is accurate and comprehensive
- [ ] **Cookie consent implemented** (if using cookies)
- [ ] **User consent for data collection**
- [ ] **Data subject rights implemented**
  - Right to access data
  - Right to delete data
  - Right to data portability

### Third-Party Compliance
- [ ] **Data attribution displayed**
  - OpenAlex CC BY 4.0 attribution in UI
  - Other third-party licenses acknowledged
  - Copyright notices visible
- [ ] **Third-party API usage disclosed**
  - User notification in UI
  - Documentation updated
- [ ] **License compliance**
  - All dependencies are compatible
  - License file is updated
  - FOSS notices included

### Content Compliance
- [ ] **No illegal content**
  - Content moderation in place (if UGC)
  - Illegal content reporting mechanism
- [ ] **Terms of Service page is live**
- [ ] **DMCA policy** (if applicable)
- [ ] **Compliance with local laws**
  - GDPR (EU)
  - CCPA (California)
  - Cybersecurity Law (China)

---

## Monitoring & Observability

### Logging
- [ ] Comprehensive logging enabled
  - Application logs
  - Access logs
  - Error logs
  - Audit logs (for sensitive operations)
- [ ] Log level appropriate for production
- [ ] Sensitive data is not logged
- [ ] Log rotation configured
- [ ] Log retention policy enforced

### Metrics
- [ ] Application metrics are collected
  - Request rate
  - Error rate
  - Response time
  - Resource usage (CPU, memory, disk)
- [ ] Business metrics are tracked
  - User signups
  - Feature usage
  - Conversion rates
- [ ] Metrics dashboards are updated
- [ ] Alerts are configured for critical metrics

### Tracing
- [ ] Distributed tracing enabled (microservices)
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Performance monitoring set up (APM)
- [ ] User session replay (if applicable)

---

## Infrastructure Readiness

### Scaling
- [ ] Auto-scaling configured (if needed)
- [ ] Load balancing is configured
- [ ] Database can handle expected load
- [ ] CDN is configured for static assets
- [ ] Caching strategy is implemented

### Backup & Recovery
- [ ] Automated backups configured
  - Database backups
  - File storage backups
  - Configuration backups
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] RTO/RPO defined and met

### Networking
- [ ] DNS is configured and propagated
- [ ] SSL/TLS certificate is valid and renewed
- [ ] Firewall rules are configured
- [ ] VPC/network isolation (if applicable)
- [ ] CDN is properly configured

---

## Testing

### Smoke Tests
- [ ] Homepage loads successfully
- [ ] Login flow works
- [ ] Core functionality is accessible
- [ ] Database connection is healthy
- [ ] External API connections work

### Integration Tests
- [ ] API endpoints respond correctly
- [ ] Third-party integrations work
- [ ] Authentication/authorization flow works
- [ ] Payment processing works (if applicable)
- [ ] Email notifications are sent

### Performance Tests
- [ ] Load testing completed
  - Response time within SLA
  - No errors under expected load
  - System scales horizontally
- [ ] Database query performance is acceptable
- [ ] Page load time is acceptable (<3s)
- [ ] Resource usage is within limits

### Security Tests
- [ ] Dependency vulnerability scan completed
  - No critical or high vulnerabilities
  - Vulnerabilities are documented or fixed
- [ ] Static analysis (SAST) completed
- [ ] Dynamic analysis (DAST) completed (if applicable)
- [ ] Penetration testing (if applicable)

---

## Deployment Process

### Deployment Steps
- [ ] Deployment window approved
- [ ] Stakeholders notified
- [ ] Database migration executed
- [ ] Application deployed
- [ ] Smoke tests pass
- [ ] Feature flags enabled (if applicable)
- [ ] Health checks pass

### Post-Deployment
- [ ] Monitor application for 30 minutes
- [ ] Check error rates
- [ ] Verify user flows work
- [ ] Confirm data integrity
- [ ] Send success notification

### Rollback Plan
- [ ] Rollback procedure documented
- [ ] Database rollback tested (if needed)
- [ ] Rollback time is <15 minutes
- [ ] Stakeholders know rollback procedure

---

## Incident Response

### Preparation
- [ ] Runbook is updated
- [ ] On-call schedule is set
- [ ] Incident communication channels defined
- [ ] Monitoring dashboards are accessible

### During Deployment
- [ ] Team is available during deployment
- [ ] Communication channel is active
- [ ] Issue tracking is ready
- [ ] Escalation path is clear

---

## Documentation

### Deployment Documentation
- [ ] Release notes published
- [ ] Changelog updated
- [ ] Known issues documented
- [ ] Migration guide provided (if needed)
- [ ] API documentation updated

### Operations Documentation
- [ ] Operations runbook updated
- [ ] Troubleshooting guide updated
- [ ] Onboarding docs updated (if applicable)
- [ ] Architecture diagrams updated (if needed)

---

## Compliance & Legal

### Regulatory Compliance
- [ ] GDPR compliance verified
- [ ] CCPA compliance verified
- [ ] Industry-specific regulations met (if applicable)
- [ ] Data protection impact assessment completed (if needed)

### Legal Review
- [ ] Terms of Service reviewed
- [ ] Privacy Policy reviewed
- [ ] Cookie Policy reviewed (if applicable)
- [ ] Third-party agreements reviewed

---

## Sign-off

### Development Team
- [ ] Lead Developer: _________________ Date: _______
- [ ] Code Reviewer: _________________ Date: _______
- [ ] QA Engineer: _________________ Date: _______

### Operations Team
- [ ] DevOps Engineer: _________________ Date: _______
- [ ] Site Reliability Engineer: _________________ Date: _______

### Management
- [ ] Product Manager: _________________ Date: _______
- [ ] Engineering Manager: _________________ Date: _______

### Final Approval
- [ ] Approved for Production: [ ] Yes [ ] No
- [ ] Approved by: _________________ Date: _______
- [ ] Deployment window: ___________________
- [ ] Rollback window: ___________________

---

## Common Deployment Failures

### P0 - Critical (Block Deployment)
1. **Hardcoded secrets in production**
2. **Missing or invalid SSL certificate**
3. **Database migration failure**
4. **Critical security vulnerability**
5. **Smoke tests fail**

### P1 - High (Fix Before Next Deployment)
1. **Missing Privacy Policy page**
2. **No rate limiting on public APIs**
3. **High error rate (>5%)**
4. **Performance degradation (>2x slower)**
5. **Missing data attribution**

### P2 - Medium (Monitor and Plan Fix)
1. **Minor security vulnerabilities**
2. **Documentation gaps**
3. **Minor UI inconsistencies**
4. **Code style violations**

---

## References

- [Reviewer Checklist](./reviewer-checklist.md)
- [Compliance Checklist](./compliance-checklist.md)
- [Incident Response Plan](../operations/incident-response.md)
- [Security Best Practices](./compliance-checklist.md)

---

*Last updated: 2026-03-30*
