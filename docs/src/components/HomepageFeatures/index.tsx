import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'ML Infrastructure',
    Svg: require('@site/static/img/ml_infrastructure.svg').default,
    description: (
      <>
        Building scalable machine learning systems and recommendation infrastructure.
        Experienced with Apache Spark, Apache Kafka, and distributed computing.
      </>
    ),
  },
  {
    title: 'Distributed Systems',
    Svg: require('@site/static/img/distributed_systems.svg').default,
    description: (
      <>
        Designing and implementing reliable, high-performance distributed systems.
        Proficient in Java, Python, gRPC, and Trino for data processing at scale.
      </>
    ),
  },
  {
    title: 'Full-Stack Development',
    Svg: require('@site/static/img/fullstack_dev.svg').default,
    description: (
      <>
        Building end-to-end solutions from React frontends to backend services.
        Experience with AWS services, TypeScript, and modern web technologies.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <h2 className="text--center" style={{marginBottom: '2rem'}}>Skills & Expertise</h2>
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
