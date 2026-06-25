import React, { useState } from 'react';
import InstitutionList from './InstitutionList';
import InstitutionDashboard from './InstitutionDashboard';

export default function InstitutionPage() {
  const [selectedInstitution, setSelectedInstitution] = useState(null);

  return (
    <>
      <InstitutionList
        onSelect={setSelectedInstitution}
      />

      <Modal
        open={!!selectedInstitution}
        onClose={() => setSelectedInstitution(null)}
        title="Institution Compliance Profile"
      >
        <InstitutionDashboard
          institutionCode={selectedInstitution}
        />
      </Modal>
    </>
  );
}