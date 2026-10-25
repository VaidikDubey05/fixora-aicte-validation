import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { RuleEditor, RulePackData } from '../../components/RuleEditor';
import { Skeleton } from '../../components/Skeleton';
import api from '../../lib/api';
import {
  useRulePack,
  useRulePackSubmit,
  useRulePackApprove,
  useRulePackTest,
} from '../../api';

export default function RuleEditorPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const packId = id && id !== 'new' && id !== 'editor' ? id : 'EOA-CHECKLIST';

  const { data: packData, isLoading, isError, refetch } = useRulePack(packId);
  const submitPack = useRulePackSubmit();
  const approvePack = useRulePackApprove();
  const testPack = useRulePackTest();

  const [notification, setNotification] = useState<string | null>(null);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  const activeVersion =
    (packData as any)?.versions?.find((v: any) => v.is_active) ||
    (packData as any)?.versions?.[0];

  const handleSave = async (yaml: string) => {
    try {
      setErrorNotice(null);
      await api.post('/rule-packs', {
        id: packData?.id || packId,
        name: packData?.name || 'Statutory AICTE APH Rule Pack',
        description: packData?.description || 'Deterministic rule definitions',
        version: activeVersion?.version ? `${activeVersion.version}.1` : 'v1.1',
        rules_yaml: yaml,
      });
      setNotification('Draft rule pack version saved successfully.');
      setTimeout(() => setNotification(null), 4000);
      refetch();
    } catch (err: any) {
      setErrorNotice(err?.response?.data?.detail || 'Failed to save rule pack draft.');
      setTimeout(() => setErrorNotice(null), 5000);
      throw err;
    }
  };

  const handleSubmitForApproval = async (version: string) => {
    try {
      setErrorNotice(null);
      await submitPack.mutateAsync({
        id: packData?.id || packId,
        version: version || activeVersion?.version || 'v1.0',
      });
      setNotification('Rule pack version submitted for dual-authorization checker review.');
      setTimeout(() => setNotification(null), 4000);
      refetch();
    } catch (err: any) {
      setErrorNotice(err?.response?.data?.detail || 'Failed to submit rule pack for review.');
      setTimeout(() => setErrorNotice(null), 5000);
      throw err;
    }
  };

  const handleApprove = async (version: string) => {
    try {
      setErrorNotice(null);
      await approvePack.mutateAsync({
        id: packData?.id || packId,
        version: version || activeVersion?.version || 'v1.0',
      });
      setNotification('Rule pack approved by checker and activated with immutable ledger hash.');
      setTimeout(() => setNotification(null), 4000);
      refetch();
    } catch (err: any) {
      setErrorNotice(
        err?.response?.data?.detail ||
          'Approval failed: Author cannot approve own rule pack (Maker-Checker violation).'
      );
      setTimeout(() => setErrorNotice(null), 6000);
      throw err;
    }
  };

  const handleTestRule = async (yaml: string, context: Record<string, any>) => {
    try {
      setErrorNotice(null);
      const res = await testPack.mutateAsync({
        id: packData?.id || packId,
        rules_yaml: yaml,
        case_context: context,
      });
      setNotification(`Evaluated ${res.items_evaluated} statutory rules successfully.`);
      setTimeout(() => setNotification(null), 3000);
      return res;
    } catch (err: any) {
      setErrorNotice(err?.response?.data?.detail || 'Rule simulation failed.');
      setTimeout(() => setErrorNotice(null), 5000);
      throw err;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-6xl mx-auto p-4 sm:p-6">
        <Skeleton variant="card" className="h-10" />
        <Skeleton variant="card" className="h-[600px]" />
      </div>
    );
  }

  if (isError && id && id !== 'new' && id !== 'editor') {
    return (
      <div className="p-8 rounded-2xl bg-surface border border-danger/30 text-center space-y-4 max-w-2xl mx-auto shadow-card">
        <div className="w-12 h-12 rounded-full bg-danger/10 text-danger flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-text">Failed to load rule pack {id}</h2>
        <p className="text-xs text-muted">
          The requested statutory rule pack could not be retrieved from the engine.
        </p>
        <button
          type="button"
          onClick={() => navigate('/admin/rules')}
          className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary/90 transition-colors shadow-xs"
        >
          Return to Rule Registry
        </button>
      </div>
    );
  }

  const packObj: RulePackData = {
    id: packData?.id || packId,
    name: packData?.name || 'Statutory AICTE APH Deterministic Rule Specification',
    description: packData?.description || 'Governing statutory rules for Extension of Approval evaluation',
    status: (packData as any)?.status || 'Draft',
    versions: (packData as any)?.versions || [
      {
        version: 'v1.0',
        status: 'Approved',
        is_active: true,
        rules_yaml: `# FIXORA STATUTORY RULE PACK SPECIFICATION
pack_id: EOA-CHECKLIST
version: "v1.0"
category: STATUTORY_APH_REQUIREMENTS

thresholds:
  min_land_acreage_rural: 7.50
  min_land_acreage_urban: 4.00
  max_cadre_ratio_faculty: 15.0
  min_builtup_carpet_ratio: 0.85

rules:
  - id: R_LAND_01
    name: Contiguous Land Title Compliance
    severity: review_required
    condition: "payload.land_acreage >= thresholds.min_land_acreage_rural"
    action_if_false:
      flag_type: record_mismatch
      message: "Declared land acreage is below mandatory statutory threshold for rural campus category."
      requires_officer_action: true

  - id: R_CADRE_01
    name: Faculty-to-Student Cadre Cadence
    severity: needs_attention
    condition: "payload.student_faculty_ratio <= thresholds.max_cadre_ratio_faculty"
    action_if_false:
      flag_type: incomplete
      message: "Cadre ratio deviates from AICTE standard 1:15 ratio."
`,
        created_by: 1,
        approved_by: 2,
        created_at: new Date().toISOString(),
      },
    ],
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Top back navigation */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/admin/rules')}
          className="px-3 py-1.5 rounded-xl border border-border bg-surface text-muted hover:text-text flex items-center gap-1.5 text-xs font-mono transition-colors shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Rule Registry</span>
        </button>

        <span className="text-xs font-mono text-muted flex items-center gap-1.5 bg-surface-alt px-3 py-1 rounded-xl border border-border">
          <ShieldCheck className="w-3.5 h-3.5 text-primary" />
          <span>Maker-Checker Dual-Authorization Enforced</span>
        </span>
      </div>

      {notification && (
        <div className="p-3.5 rounded-xl bg-success/15 border border-success/30 text-xs text-success font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {errorNotice && (
        <div className="p-3.5 rounded-xl bg-danger/15 border border-danger/30 text-xs text-danger font-semibold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorNotice}</span>
        </div>
      )}

      {/* Main IDE Component */}
      <RuleEditor
        pack={packObj}
        activeVersion={activeVersion || packObj.versions?.[0]}
        onSaveDraft={handleSave}
        onSubmitForApproval={handleSubmitForApproval}
        onApproveVersion={handleApprove}
        onRunTest={handleTestRule}
        isSubmitting={submitPack.isPending}
        isApproving={approvePack.isPending}
        isTesting={testPack.isPending}
      />
    </div>
  );
}
