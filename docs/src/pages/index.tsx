import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">Hi, I'm {siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/blog">
            Read My Blog
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="https://linkedin.com/in/wei-li-ca">
            Connect on LinkedIn
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="mailto:xavierliwei@gmail.com">
            Email Me
          </Link>
        </div>
      </div>
    </header>
  );
}

function AboutSection() {
  return (
    <section className={styles.aboutSection}>
      <div className="container">
        <h2>About Me</h2>
        <p>
          I am a senior software engineer with 6+ years of experience in developing and
          deploying scalable, reliable, and secure software solutions. My current focus is
          on machine learning infrastructure, where I work on recommendation systems at TikTok.
        </p>
        <p>
          I'm passionate about building robust distributed systems and leveraging modern
          technologies to solve complex problems at scale.
        </p>
      </div>
    </section>
  );
}

function ExperienceSection() {
  const experiences = [
    {
      company: 'TikTok (ByteDance)',
      role: 'Senior Software Engineer',
      period: 'Aug 2025 - Present',
      location: 'San Jose, CA',
      description: 'Working on Recommendation Infrastructure, building ML systems at scale.',
    },
    {
      company: 'LinkedIn',
      role: 'Senior Software Engineer',
      period: 'Aug 2021 - Aug 2025',
      location: 'Sunnyvale, CA',
      description: 'Led DMA compliance auditing on metadata, organized working groups, and built data infrastructure using Apache Kafka and Apache Spark.',
    },
    {
      company: 'Amazon Web Services (AWS)',
      role: 'Software Development Engineer',
      period: 'Apr 2019 - Jul 2020',
      location: 'East Palo Alto, CA',
      description: 'Worked on Quantum Ledger Database (QLDB), implementing console frontend with React, Redux, and TypeScript.',
    },
    {
      company: 'T. Rowe Price',
      role: 'Software Engineer',
      period: 'Sep 2018 - Apr 2019',
      location: 'Washington DC-Baltimore Area',
      description: 'Implemented data ETL pipeline with AWS Step Function, Lambda Function, and DynamoDB.',
    },
  ];

  return (
    <section className={styles.experienceSection}>
      <div className="container">
        <h2>Experience</h2>
        <div className={styles.timeline}>
          {experiences.map((exp, idx) => (
            <div key={idx} className={styles.timelineItem}>
              <div className={styles.timelineContent}>
                <h3>{exp.role}</h3>
                <h4>{exp.company}</h4>
                <p className={styles.period}>{exp.period} | {exp.location}</p>
                <p>{exp.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function EducationSection() {
  const education = [
    {
      school: 'Carnegie Mellon University',
      degree: "Master's Degree",
      period: '2020 - 2021',
    },
    {
      school: 'Columbia College, Columbia University',
      degree: "Bachelor's Degree, Mathematics",
      period: '2013 - 2017',
    },
  ];

  return (
    <section className={styles.educationSection}>
      <div className="container">
        <h2>Education</h2>
        <div className={styles.educationGrid}>
          {education.map((edu, idx) => (
            <div key={idx} className={styles.educationCard}>
              <h3>{edu.school}</h3>
              <p>{edu.degree}</p>
              <p className={styles.period}>{edu.period}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title} - Personal Website`}
      description="Personal website and blog of Wei Li, Senior Software Engineer at TikTok specializing in ML Infrastructure">
      <HomepageHeader />
      <main>
        <AboutSection />
        <HomepageFeatures />
        <ExperienceSection />
        <EducationSection />
      </main>
    </Layout>
  );
}
