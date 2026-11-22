import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createGroup,
  deleteGroup,
  listGroupCandidateUsers,
  listGroups,
  removeGroupMember,
  updateGroup,
  upsertGroupMember,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { GroupItem, GroupMember } from "../types";

interface CandidateUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

export default function GroupsPage() {
  const { currentUser } = useAuth();
  const { showToast } = useToast();

  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [candidates, setCandidates] = useState<CandidateUser[]>([]);
  const [selected, setSelected] = useState<GroupItem | null>(null);
  const [loading, setLoading] = useState(true);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [canCreate, setCanCreate] = useState(true);
  const [canEdit, setCanEdit] = useState(false);
  const [canAssign, setCanAssign] = useState(false);

  const [renameValue, setRenameValue] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = async (selectId?: number) => {
    setLoading(true);
    try {
      const [groupData, userData] = await Promise.all([
        listGroups(),
        listGroupCandidateUsers(),
      ]);
      setGroups(groupData);
      setCandidates(userData);
      const next =
        groupData.find((g) => g.id === (selectId ?? selected?.id)) ||
        groupData[0] ||
        null;
      setSelected(next);
      setRenameValue(next?.name || "");
      setConfirmDelete(false);
    } catch (err: any) {
      showToast(err?.message || "Failed to load groups", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const created = await createGroup({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
      });
      setNewName("");
      setNewDesc("");
      setShowCreateForm(false);
      showToast(`Group "${created.name}" created`, "success");
      await load(created.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to create group", "error");
    }
  };

  const handleRename = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !renameValue.trim()) return;
    try {
      const updated = await updateGroup(selected.id, {
        name: renameValue.trim(),
        description: selected.description || undefined,
      });
      showToast("Group updated", "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Only the owner can rename this group", "error");
    }
  };

  const handleDeleteGroup = async () => {
    if (!selected) return;
    try {
      await deleteGroup(selected.id);
      showToast(`Deleted "${selected.name}"`, "success");
      setSelected(null);
      setConfirmDelete(false);
      await load();
    } catch (err: any) {
      showToast(err?.message || "Only the owner can delete this group", "error");
    }
  };

  const handleAddMember = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !selectedCandidateId) return;
    try {
      const updated = await upsertGroupMember(selected.id, {
        user_id: Number(selectedCandidateId),
        can_create: canCreate,
        can_edit: canEdit,
        can_assign: canAssign,
      });
      setSelectedCandidateId("");
      showToast("Member added with selected permissions", "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to add member", "error");
    }
  };

  const handleTogglePermission = async (
    m: GroupMember,
    field: "can_create" | "can_edit" | "can_assign"
  ) => {
    if (!selected) return;
    try {
      const updated = await upsertGroupMember(selected.id, {
        user_id: m.user_id,
        can_create: field === "can_create" ? !m.can_create : m.can_create,
        can_edit: field === "can_edit" ? !m.can_edit : m.can_edit,
        can_assign: field === "can_assign" ? !m.can_assign : m.can_assign,
      });
      showToast(`Updated permissions for ${m.name}`, "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to update permissions", "error");
    }
  };

  const handleRemoveMember = async (uid: number, name: string) => {
    if (!selected) return;
    try {
      const updated = await removeGroupMember(selected.id, uid);
      showToast(`Removed ${name} from group`, "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to remove member", "error");
    }
  };

  const isOwner = Boolean(
    selected && currentUser && selected.owner_id === currentUser.id
  );
  const existingMemberIds = new Set(selected?.members.map((m) => m.user_id) || []);
  const availableUsers = candidates.filter(
    (c) => c.id !== selected?.owner_id && !existingMemberIds.has(c.id)
  );

  return (
    <div className="container">
      <div className="page-hero">
        <div>
          <span className="page-hero-eyebrow">RBAC Collaboration</span>
          <h1>Shared Triage Groups</h1>
          <p>
            Share vulnerability reports in teams with granular Create, Edit, and Assign permissions.
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateForm((v) => !v)}
        >
          {showCreateForm ? "Close" : "+ New Group"}
        </button>
      </div>

      {showCreateForm && (
        <form
          className="card"
          onSubmit={handleCreate}
          style={{ marginBottom: "1.25rem", display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}
        >
          <input
            placeholder="Group name (e.g., API Security Team)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
            style={{ minWidth: 220 }}
          />
          <input
            placeholder="Short description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            style={{ flex: 1, minWidth: 240 }}
          />
          <button className="btn btn-primary" type="submit">Create Group</button>
          <button className="btn btn-secondary" type="button" onClick={() => setShowCreateForm(false)}>
            Cancel
          </button>
        </form>
      )}

      {loading ? (
        <div className="card">Loading shared groups...</div>
      ) : groups.length === 0 ? (
        <div className="card">
          <h3>No Shared Groups Yet</h3>
          <p className="muted">Create your first group to collaborate with analysts and researchers.</p>
        </div>
      ) : (
        <div className="groups-layout">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Your Groups ({groups.length})</h3>
            {groups.map((g) => (
              <button
                key={g.id}
                onClick={() => {
                  setSelected(g);
                  setRenameValue(g.name);
                  setConfirmDelete(false);
                }}
                className={`group-item-btn ${selected?.id === g.id ? "active" : ""}`}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                  <strong>{g.name}</strong>
                  {g.owner_id === currentUser?.id && <span className="perm-pill on">Owner</span>}
                </div>
                <div className="muted" style={{ fontSize: "0.78rem", marginTop: "0.25rem" }}>
                  {g.members.length} member(s) • {g.owner_email}
                </div>
              </button>
            ))}
          </div>

          {selected && (
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{selected.name}</h2>
                  <p className="muted" style={{ marginTop: "0.3rem" }}>
                    Owner: <strong>{selected.owner_email}</strong> • {selected.description || "No description"}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <Link to={`/reports/new?group_id=${selected.id}`} className="btn btn-primary btn-sm">
                    + Submit Report to Group
                  </Link>
                  <Link to={`/reports?group_id=${selected.id}`} className="btn btn-secondary btn-sm">
                    View Group Reports
                  </Link>
                  {isOwner && !confirmDelete && (
                    <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelete(true)}>
                      Delete Group
                    </button>
                  )}
                </div>
              </div>

              {isOwner && confirmDelete && (
                <div className="bulk-bar" style={{ marginTop: "0.75rem", borderColor: "rgba(239,68,68,0.45)" }}>
                  <span>Delete <strong>{selected.name}</strong>? Group reports will remain intact.</span>
                  <div className="bulk-bar-actions">
                    <button className="btn btn-danger btn-sm" onClick={handleDeleteGroup}>
                      Confirm Delete
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setConfirmDelete(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {isOwner && (
                <form
                  onSubmit={handleRename}
                  style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", marginBottom: "1.25rem", flexWrap: "wrap" }}
                >
                  <input
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    placeholder="Rename group..."
                    style={{ flex: 1, minWidth: 200 }}
                  />
                  <button className="btn btn-secondary btn-sm" type="submit">Save Name</button>
                </form>
              )}

              <h3 style={{ marginBottom: "0.6rem" }}>
                Members & Permissions ({selected.members.length})
              </h3>
              {isOwner && (
                <p className="muted" style={{ fontSize: "0.82rem", marginTop: 0 }}>
                  Tip: Click any permission badge below to toggle it live.
                </p>
              )}

              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Create Reports</th>
                      <th>Edit Reports</th>
                      <th>Assign / Triage</th>
                      {isOwner && <th>Action</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {selected.members.map((m) => (
                      <tr key={m.user_id}>
                        <td>
                          <strong>{m.name}</strong>
                          <div className="muted" style={{ fontSize: "0.78rem" }}>{m.email}</div>
                        </td>
                        <td>
                          <button
                            type="button"
                            disabled={!isOwner}
                            onClick={() => handleTogglePermission(m, "can_create")}
                            className={`perm-pill-btn perm-pill ${m.can_create ? "on" : "off"}`}
                          >
                            {m.can_create ? "Allowed" : "Denied"}
                          </button>
                        </td>
                        <td>
                          <button
                            type="button"
                            disabled={!isOwner}
                            onClick={() => handleTogglePermission(m, "can_edit")}
                            className={`perm-pill-btn perm-pill ${m.can_edit ? "on" : "off"}`}
                          >
                            {m.can_edit ? "Allowed" : "Denied"}
                          </button>
                        </td>
                        <td>
                          <button
                            type="button"
                            disabled={!isOwner}
                            onClick={() => handleTogglePermission(m, "can_assign")}
                            className={`perm-pill-btn perm-pill ${m.can_assign ? "on" : "off"}`}
                          >
                            {m.can_assign ? "Allowed" : "Denied"}
                          </button>
                        </td>
                        {isOwner && (
                          <td>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleRemoveMember(m.user_id, m.name)}
                            >
                              Remove
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                    {selected.members.length === 0 && (
                      <tr>
                        <td colSpan={isOwner ? 5 : 4} className="muted">
                          No members yet. Add a teammate below.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {isOwner && (
                <form onSubmit={handleAddMember} style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid rgba(148,163,184,0.2)" }}>
                  <h4 style={{ marginTop: 0 }}>Add Team Member</h4>
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => setSelectedCandidateId(e.target.value)}
                    required
                    style={{ width: "100%", marginBottom: "0.75rem" }}
                  >
                    <option value="">Select a user by name & email...</option>
                    {availableUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.email}) — {u.role}
                      </option>
                    ))}
                  </select>

                  <div className="perm-grid">
                    <button
                      type="button"
                      onClick={() => setCanCreate((v) => !v)}
                      className={`perm-toggle-card ${canCreate ? "selected" : ""}`}
                    >
                      <span className="perm-toggle-title">
                        Create Reports <span>{canCreate ? "✅" : "○"}</span>
                      </span>
                      <span className="perm-toggle-desc">Submit new vulnerability reports into this group.</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setCanEdit((v) => !v)}
                      className={`perm-toggle-card ${canEdit ? "selected" : ""}`}
                    >
                      <span className="perm-toggle-title">
                        Edit Reports <span>{canEdit ? "✅" : "○"}</span>
                      </span>
                      <span className="perm-toggle-desc">Modify group reports while in New status.</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setCanAssign((v) => !v)}
                      className={`perm-toggle-card ${canAssign ? "selected" : ""}`}
                    >
                      <span className="perm-toggle-title">
                        Assign / Triage <span>{canAssign ? "✅" : "○"}</span>
                      </span>
                      <span className="perm-toggle-desc">Update triage status and severity inside this group.</span>
                    </button>
                  </div>

                  <button className="btn btn-primary" type="submit" disabled={!selectedCandidateId}>
                    Add Member to Group
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
