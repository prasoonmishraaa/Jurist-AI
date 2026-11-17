import React from 'react';
import { IJudicialTreatmentAssessment, QualitativeResearchMeta } from '../../types';
import { JudicialTreatmentView } from './JudicialTreatmentView';

interface OutcomeMeterProps {
  assessment?: IJudicialTreatmentAssessment;
  prediction?: QualitativeResearchMeta;
}

export const OutcomeMeter: React.FC<OutcomeMeterProps> = ({ assessment, prediction }) => {
  return <JudicialTreatmentView assessment={assessment} meta={prediction} />;
};
