import { useState, FormEvent } from "react";
import client from "../api/client";

interface AssessmentType {
  name: string;
  weight: number;
}

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

const CreateProjectModal = ({ onClose, onCreated }: Props) => {
  const [name, setName] = useState("");
  const [academicYearStart, setAcademicYearStart] = useState(new Date().getFullYear());
  const [description, setDescription] = useState("");
  const [assessmentTypes, setAssessmentTypes] = useState<AssessmentType[]>([
    { name: "", weight: 0 },
  ]);
  const [error, setError] = useState("");

  const addAssessmentType = () => {
    setAssessmentTypes([...assessmentTypes, { name: "", weight: 0 }]);
  };

  const removeAssessmentType = (index: number) => {
    if (assessmentTypes.length === 1) return; // at least one row
    setAssessmentTypes(assessmentTypes.filter((_, i) => i !== index));
  };

  const updateAssessment = (index: number, field: keyof AssessmentType, value: string | number) => {
    const updated = [...assessmentTypes];
    updated[index] = { ...updated[index], [field]: value };
    setAssessmentTypes(updated);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation
    const totalWeight = assessmentTypes.reduce((sum, at) => sum + at.weight, 0);
    if (Math.abs(totalWeight - 100) > 0.01) {
      setError("Assessment weights must sum to 100.");
      return;
    }
    if (assessmentTypes.some((at) => !at.name.trim())) {
      setError("All assessment types must have a name.");
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
      onCreated();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to create project";
      setError(msg);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">New Project</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
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
              Assessment Types
            </legend>
            {assessmentTypes.map((at, idx) => (
              <div key={idx} className="flex items-center space-x-2 mb-2">
                <input
                  type="text"
                  placeholder="Name (e.g. quiz)"
                  value={at.name}
                  onChange={(e) => updateAssessment(idx, "name", e.target.value)}
                  className="flex-1 border border-gray-300 rounded-md p-2 text-sm"
                  required
                />
                <input
                  type="number"
                  placeholder="Weight"
                  value={at.weight}
                  onChange={(e) => updateAssessment(idx, "weight", Number(e.target.value))}
                  className="w-20 border border-gray-300 rounded-md p-2 text-sm"
                  min={0}
                  max={100}
                  step={0.1}
                  required
                />
                {assessmentTypes.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeAssessmentType(idx)}
                    className="text-red-500 hover:text-red-700 text-xl leading-none px-1"
                  >
                    &times;
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addAssessmentType}
              className="mt-1 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              + Add assessment type
            </button>
          </fieldset>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
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
    </div>
  );
};

export default CreateProjectModal;