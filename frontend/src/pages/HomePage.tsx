import { useState, useEffect, useCallback, FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import client from "../api/client";

interface Project {
  id: number;
  name: string;
  academic_year_start: number;
  description?: string;
  user_id: number;
}

interface AssessmentType {
  name: string;
  weight: number;
}

const HomePage = () => {
  const { logout } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // --- create form state ---
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState("");
  const [academicYearStart, setAcademicYearStart] = useState(new Date().getFullYear());
  const [description, setDescription] = useState("");
  const [assessmentTypes, setAssessmentTypes] = useState<AssessmentType[]>([
    { name: "", weight: 0 },
  ]);
  const [formError, setFormError] = useState("");

  const fetchProjects = useCallback(async () => {
    try {
      setError("");
      const res = await client.get("/projects");
      setProjects(res.data);
    } catch (err: any) {
      setError("Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleDelete = async (projectId: number) => {
    if (!confirm("Delete this project and all its data?")) return;
    try {
      await client.delete(`/projects/${projectId}`);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
    } catch (err: any) {
      alert("Delete failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const addAssessmentType = () => {
    setAssessmentTypes([...assessmentTypes, { name: "", weight: 0 }]);
  };

  const removeAssessmentType = (index: number) => {
    if (assessmentTypes.length === 1) return;
    setAssessmentTypes(assessmentTypes.filter((_, i) => i !== index));
  };

  // Generic update to avoid TS error
  const updateAssessment = <K extends keyof AssessmentType>(
    index: number,
    field: K,
    value: AssessmentType[K]
  ) => {
    const updated = [...assessmentTypes];
    updated[index] = { ...updated[index], [field]: value };
    setAssessmentTypes(updated);
  };

  const handleCreateProject = async (e: FormEvent) => {
    e.preventDefault();
    setFormError("");

    const totalWeight = assessmentTypes.reduce((sum, at) => sum + at.weight, 0);
    if (Math.abs(totalWeight - 100) > 0.01) {
      setFormError("Assessment weights must sum to 100%.");
      return;
    }
    if (assessmentTypes.some((at) => !at.name.trim())) {
      setFormError("All assessment types need a name.");
      return;
    }

    const payload = {
      name,
      academic_year_start: academicYearStart,
      description: description || null,
      assessment_types: assessmentTypes.map((at) => ({
        name: at.name.trim(),
        weight: at.weight,
      })),
    };

    try {
      await client.post("/projects", payload);
      setName("");
      setAcademicYearStart(new Date().getFullYear());
      setDescription("");
      setAssessmentTypes([{ name: "", weight: 0 }]);
      setShowCreateForm(false);
      fetchProjects();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to create project");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top navigation bar */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between h-16 items-center">
          <h1 className="text-xl font-bold text-gray-800">EduAnalytics</h1>
          <button
            onClick={logout}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Projects</h2>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
          >
            {showCreateForm ? "Cancel" : "+ New Project"}
          </button>
        </div>

        {/* Inline creation form */}
        {showCreateForm && (
          <div className="bg-white shadow-md rounded-lg border border-gray-200 p-4 sm:p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Create a new project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Project Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Academic Year Start</label>
                <input
                  type="number"
                  required
                  value={academicYearStart}
                  onChange={(e) => setAcademicYearStart(Number(e.target.value))}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Description (optional)</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  rows={2}
                />
              </div>

              <fieldset>
                <legend className="block text-sm font-medium text-gray-700 mb-2">
                  Assessment Types (weights must sum to 100%)
                </legend>
                <div className="space-y-2">
                  {assessmentTypes.map((at, idx) => (
                    <div key={idx} className="flex items-center space-x-2">
                      <input
                        type="text"
                        placeholder="e.g. Quiz"
                        value={at.name}
                        onChange={(e) => updateAssessment(idx, "name", e.target.value)}
                        className="flex-1 border border-gray-300 rounded-md p-2 text-sm"
                        required
                      />
                      <div className="flex items-center space-x-1">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={at.weight === 0 ? "" : at.weight}
                          onChange={(e) => {
                            const raw = e.target.value;
                            const num = raw === "" ? 0 : Number(raw);
                            updateAssessment(idx, "weight", isNaN(num) ? 0 : num);
                          }}
                          className="w-16 border border-gray-300 rounded-md p-2 text-sm text-center"
                          placeholder="0"
                        />
                        <span className="text-gray-500 text-sm">%</span>
                      </div>
                      {assessmentTypes.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeAssessmentType(idx)}
                          title="Remove"
                          className="text-gray-400 hover:text-red-600 p-1"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={addAssessmentType}
                  className="mt-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  + Add assessment type
                </button>
              </fieldset>

              {formError && <p className="text-red-500 text-sm">{formError}</p>}

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        )}

        {loading && <p className="text-gray-500">Loading...</p>}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {!loading && !error && projects.length === 0 && !showCreateForm && (
          <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center">
            <p className="text-gray-500 text-lg">No projects yet. Create one to get started.</p>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white rounded-lg shadow p-5 border border-gray-200"
            >
              <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
              <p className="text-sm text-gray-500 mt-1">
                Academic year: {project.academic_year_start}
              </p>
              {project.description && (
                <p className="text-sm text-gray-600 mt-2">{project.description}</p>
              )}
              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => handleDelete(project.id)}
                  className="text-red-600 hover:text-red-800 text-sm font-medium"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default HomePage;