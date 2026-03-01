import React from 'react';

const LAST_UPDATED = '2026-03-01';
const CONTACT_EMAIL = 'support@masteryi.app';

const Privacy: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#f7f4ed] text-neutral-900 px-6 py-12">
      <main className="max-w-3xl mx-auto bg-white/80 border border-neutral-200 rounded-sm p-8 md:p-12 space-y-8">
        <header className="space-y-3">
          <p className="text-xs tracking-[0.2em] text-neutral-500">MASTERYI</p>
          <h1 className="text-3xl md:text-4xl font-black tracking-[0.06em]">Privacy Policy</h1>
          <p className="text-sm text-neutral-500">Last updated: {LAST_UPDATED}</p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">1. Overview</h2>
          <p className="leading-relaxed">
            This Privacy Policy explains how MasterYi collects, uses, and protects your personal information when you
            use our web and mobile services.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">2. Information We Collect</h2>
          <p className="leading-relaxed">
            We may collect account identifiers (for example Google/Apple sign-in identity), basic profile data,
            app usage data, divination input and output content, purchase status, and device-level technical logs
            for reliability and abuse prevention.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">3. How We Use Information</h2>
          <p className="leading-relaxed">
            We use data to provide divination features, maintain account and billing status, improve service quality,
            prevent fraud or misuse, and comply with legal obligations.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">4. Third-Party Services</h2>
          <p className="leading-relaxed">
            Our service may integrate third-party platforms, including Google Sign-In, Apple Sign-In, and Google
            AdMob. These providers may collect or process data according to their own privacy policies.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">5. Data Retention</h2>
          <p className="leading-relaxed">
            We retain data only as long as needed for service operation, legal compliance, dispute handling, and
            security requirements.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">6. Your Rights</h2>
          <p className="leading-relaxed">
            Depending on your location, you may have rights to access, correct, delete, or limit processing of your
            personal data. You may contact us to request support.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-bold">7. Contact</h2>
          <p className="leading-relaxed">
            If you have privacy-related questions, contact us at{' '}
            <a className="underline underline-offset-4" href={`mailto:${CONTACT_EMAIL}`}>
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>
      </main>
    </div>
  );
};

export default Privacy;
