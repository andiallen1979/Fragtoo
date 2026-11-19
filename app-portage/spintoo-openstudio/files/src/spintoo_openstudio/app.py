import json
import sys
from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QHeaderView,
    QFileDialog,
)

from .assistant import AssistantError, LocalAssistant, build_request_payload
from .importers import (
    ImportError as ProfileImportError,
    import_config_files,
    import_overlay_targets,
    import_profile_catalog,
)
from .libvirt_backend import VMBackendError, list_domains
from .matrix import BuildMatrix, BuildVariant, MatrixError, MatrixStore
from .presets import load_builtin_presets
from .scheduler import BuildJob, ResourceBudget, select_startable_jobs, suggested_resource_budget


class _DraftSignals(QObject):
    succeeded = pyqtSignal(object, str)
    failed = pyqtSignal(object, str)


class _DraftWorker(QRunnable):
    def __init__(self, endpoint: str, model: str, goal: str, variants: list[BuildVariant]) -> None:
        super().__init__()
        self.endpoint = endpoint
        self.model = model
        self.goal = goal
        self.variants = variants
        self.signals = _DraftSignals()

    def run(self) -> None:
        try:
            draft = LocalAssistant(self.endpoint, self.model).draft(self.goal, self.variants)
        except AssistantError as exc:
            self.signals.failed.emit(self, str(exc))
        else:
            self.signals.succeeded.emit(self, json.dumps(draft.to_mapping(), indent=2))


class MainWindow(QMainWindow):
    _TEXT_FIELDS = (
        ("make_conf", "make.conf"),
        ("package_use", "package.use"),
        ("accept_keywords", "package.accept_keywords"),
        ("package_mask", "package.mask"),
        ("package_unmask", "package.unmask"),
        ("package_env", "package.env"),
        ("package_license", "package.license"),
        ("patches", "Patch mappings"),
        ("kernel_config", "Kernel config"),
        ("world_packages", "Guest world packages"),
        ("targets", "Build targets"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spintoo OpenStudio")
        self.resize(1180, 780)
        self.store = MatrixStore()
        self.matrix = self.store.load()
        self.current_row = -1
        self.dirty = False
        self.workers: list[_DraftWorker] = []
        self.pool = QThreadPool.globalInstance()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_matrix_tab()
        self._build_queue_tab()
        self._build_assistant_tab()
        self._build_libvirt_tab()
        self.matrix_unsaved = False
        self.name_input.textEdited.connect(self._mark_dirty)
        self.arch_input.textEdited.connect(self._mark_dirty)
        self.vcpu_input.valueChanged.connect(self._mark_dirty)
        self.memory_input.valueChanged.connect(self._mark_dirty)
        for editor in self.config_inputs.values():
            editor.textChanged.connect(self._mark_dirty)
        self.goal_input.textChanged.connect(self._refresh_ai_preview)
        self.model_input.textChanged.connect(self._refresh_ai_preview)
        self._refresh_variant_list()

    def _build_matrix_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Start from the Fragtoo Valve baseline or an empty variant, then diverge configurations as needed. "
            "Raw Portage syntax is preserved; this prototype does not write to /etc/portage or launch builds."
        ))
        split = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.variant_list = QListWidget()
        self.variant_list.currentRowChanged.connect(self._selection_changed)
        left_layout.addWidget(self.variant_list, 1)
        buttons = QHBoxLayout()
        for label, callback in (
            ("New empty", self._new_variant),
            ("Duplicate", self._duplicate_variant),
            ("Remove", self._remove_variant),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        left_layout.addLayout(buttons)
        import_buttons = QVBoxLayout()
        for label, callback in (
            ("Add preset", self._add_builtin_preset),
            ("Import external profiles", self._import_profiles),
            ("Import overlay targets", self._import_overlay_targets),
            ("Import config files", self._import_config_files),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            import_buttons.addWidget(button)
        left_layout.addLayout(import_buttons)
        split.addWidget(left)

        right = QWidget()
        form = QFormLayout(right)
        self.name_input = QLineEdit()
        self.arch_input = QLineEdit()
        self.arch_input.setPlaceholderText("amd64")
        self.vcpu_input = QSpinBox()
        self.vcpu_input.setRange(1, 256)
        self.memory_input = QSpinBox()
        self.memory_input.setRange(512, 1_048_576)
        self.memory_input.setSuffix(" MiB")
        self.config_inputs: dict[str, QPlainTextEdit] = {}
        form.addRow("Variant name", self.name_input)
        form.addRow("Gentoo architecture", self.arch_input)
        form.addRow("Requested vCPUs", self.vcpu_input)
        form.addRow("Requested memory", self.memory_input)
        for key, label in self._TEXT_FIELDS:
            editor = QPlainTextEdit()
            editor.setTabStopDistance(32)
            editor.setMaximumHeight(120)
            self.config_inputs[key] = editor
            form.addRow(label, editor)
        save_button = QPushButton("Save matrix")
        save_button.clicked.connect(self._save_matrix)
        form.addRow(save_button)
        self.matrix_status = QLabel(f"Matrix file: {self.store.path}")
        form.addRow(self.matrix_status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right)
        split.addWidget(scroll)
        split.setSizes([280, 880])

        self.tabs.addTab(page, "Build Matrix")

    def _build_queue_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Preview how many matrix builds fit the configured CPU and memory budget. "
            "This is a planning view; it does not create VMs or start builds."
        ))
        controls = QHBoxLayout()
        budget = suggested_resource_budget()
        self.budget_vcpus = QSpinBox()
        self.budget_vcpus.setRange(1, 512)
        self.budget_vcpus.setValue(min(512, budget.vcpus))
        self.budget_memory = QSpinBox()
        self.budget_memory.setRange(512, 1_048_576)
        self.budget_memory.setSuffix(" MiB")
        self.budget_memory.setValue(min(1_048_576, budget.memory_mib))
        controls.addWidget(QLabel("Total vCPU budget"))
        controls.addWidget(self.budget_vcpus)
        controls.addWidget(QLabel("Total memory budget"))
        controls.addWidget(self.budget_memory)
        preview_button = QPushButton("Preview schedule")
        preview_button.clicked.connect(self._refresh_queue_preview)
        controls.addWidget(preview_button)
        layout.addLayout(controls)
        self.queue_table = QTableWidget(0, 5)
        self.queue_table.setHorizontalHeaderLabels(("Plan", "Variant", "Target", "vCPU", "Memory"))
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.queue_table, 1)
        self.queue_status = QLabel("Import overlay targets into one or more variants to preview a schedule.")
        layout.addWidget(self.queue_status)
        self.tabs.addTab(page, "Build Queue")

    def _build_assistant_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Local AI drafts only. Select the variants and review the exact request before sending. "
            "Suggestions are never applied automatically."
        ))
        self.ai_variant_list = QListWidget()
        self.ai_variant_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ai_variant_list.itemSelectionChanged.connect(self._refresh_ai_preview)
        layout.addWidget(QLabel("Variants to include"))
        layout.addWidget(self.ai_variant_list)

        options = QHBoxLayout()
        self.endpoint_input = QLineEdit("http://localhost:11434/v1")
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Local model name")
        options.addWidget(QLabel("Local endpoint"))
        options.addWidget(self.endpoint_input, 2)
        options.addWidget(QLabel("Model"))
        options.addWidget(self.model_input, 1)
        layout.addLayout(options)

        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("What should the model compare or propose?")
        layout.addWidget(self.goal_input)
        self.ai_preview = QPlainTextEdit()
        self.ai_preview.setReadOnly(True)
        self.ai_preview.setPlaceholderText("The selected context and request preview will appear here.")
        layout.addWidget(QLabel("Request preview"))
        layout.addWidget(self.ai_preview, 2)
        action_row = QHBoxLayout()
        self.ai_status = QLabel("No request sent.")
        action_row.addWidget(self.ai_status, 1)
        send_button = QPushButton("Send selected context to local model")
        send_button.clicked.connect(self._send_ai_request)
        action_row.addWidget(send_button)
        layout.addLayout(action_row)
        self.ai_result = QPlainTextEdit()
        self.ai_result.setReadOnly(True)
        self.ai_result.setPlaceholderText("Draft response appears here for review; there is no apply button.")
        layout.addWidget(QLabel("Draft response (not applied)"))
        layout.addWidget(self.ai_result, 2)
        self.tabs.addTab(page, "AI Matrix Draft")

    def _build_libvirt_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "Read-only inventory from qemu:///system. Template creation, cloning, and build execution "
            "are planned follow-up work."
        ))
        header = QHBoxLayout()
        header.addWidget(QLabel("Libvirt guests"))
        header.addStretch(1)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_domains)
        header.addWidget(refresh_button)
        layout.addLayout(header)
        self.domain_table = QTableWidget(0, 3)
        self.domain_table.setHorizontalHeaderLabels(("Name", "State", "UUID"))
        self.domain_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.domain_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.domain_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.domain_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.domain_table, 1)
        self.vm_status = QLabel("Not connected.")
        layout.addWidget(self.vm_status)
        self.tabs.addTab(page, "Libvirt")

    def _refresh_variant_list(self) -> None:
        self.variant_list.blockSignals(True)
        self.ai_variant_list.blockSignals(True)
        self.variant_list.clear()
        self.ai_variant_list.clear()
        for variant in self.matrix.variants:
            self.variant_list.addItem(variant.name)
            self.ai_variant_list.addItem(QListWidgetItem(variant.name))
        self.variant_list.blockSignals(False)
        self.ai_variant_list.blockSignals(False)
        if self.matrix.variants:
            self.variant_list.setCurrentRow(min(max(self.current_row, 0), len(self.matrix.variants) - 1))
        self._refresh_ai_preview()

    def _selection_changed(self, row: int) -> None:
        if self.dirty and self.current_row >= 0:
            answer = QMessageBox.question(
                self,
                "Unsaved variant",
                "Save changes to the current variant before switching?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                self.variant_list.blockSignals(True)
                self.variant_list.setCurrentRow(self.current_row)
                self.variant_list.blockSignals(False)
                return
            if answer == QMessageBox.StandardButton.Save and not self._save_current_variant():
                self.variant_list.blockSignals(True)
                self.variant_list.setCurrentRow(self.current_row)
                self.variant_list.blockSignals(False)
                return
        self.current_row = row
        self._load_current_variant()

    def _load_current_variant(self) -> None:
        if self.current_row < 0:
            return
        variant = self.matrix.variants[self.current_row]
        widgets = [self.name_input, self.arch_input, self.vcpu_input, self.memory_input, *self.config_inputs.values()]
        for widget in widgets:
            widget.blockSignals(True)
        self.name_input.setText(variant.name)
        self.arch_input.setText(variant.arch)
        self.vcpu_input.setValue(variant.vcpus)
        self.memory_input.setValue(variant.memory_mib)
        for key, _label in self._TEXT_FIELDS:
            self.config_inputs[key].setPlainText(getattr(variant, key))
        for widget in widgets:
            widget.blockSignals(False)
        self.dirty = False

    def _mark_dirty(self, *_args) -> None:
        self.dirty = True

    def _capture_current_variant(self) -> BuildVariant:
        variant = BuildVariant(
            name=self.name_input.text(),
            arch=self.arch_input.text(),
            vcpus=self.vcpu_input.value(),
            memory_mib=self.memory_input.value(),
            **{key: editor.toPlainText() for key, editor in self.config_inputs.items()},
        )
        variant.validate()
        return variant

    def _save_current_variant(self) -> bool:
        if self.current_row < 0:
            return True
        try:
            variant = self._capture_current_variant()
            others = [item for index, item in enumerate(self.matrix.variants) if index != self.current_row]
            candidate = BuildMatrix([*others, variant])
            candidate.validate()
        except MatrixError as exc:
            QMessageBox.warning(self, "Invalid variant", str(exc))
            return False
        self.matrix.variants[self.current_row] = variant
        self.dirty = False
        self.matrix_unsaved = True
        self.variant_list.item(self.current_row).setText(variant.name)
        self.ai_variant_list.item(self.current_row).setText(variant.name)
        self._refresh_ai_preview()
        return True

    def _save_matrix(self) -> None:
        if not self._save_current_variant():
            return
        try:
            self.store.save(self.matrix)
        except (MatrixError, OSError) as exc:
            QMessageBox.critical(self, "Could not save matrix", str(exc))
            return
        self.matrix_unsaved = False
        self.matrix_status.setText(f"Saved matrix: {self.store.path}")

    def _import_profiles(self) -> None:
        if self.dirty and not self._save_current_variant():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Import Gentoo profile catalog", "", "JSON files (*.json)")
        if not filename:
            return
        try:
            imported = import_profile_catalog(Path(filename))
            names = {item.name.casefold() for item in self.matrix.variants}
            for variant in imported:
                base = variant.name
                name = base
                suffix = 2
                while name.casefold() in names:
                    name = f"{base} {suffix}"
                    suffix += 1
                names.add(name.casefold())
                self.matrix.variants.append(BuildVariant.from_mapping({**asdict(variant), "name": name}))
        except (ProfileImportError, MatrixError) as exc:
            QMessageBox.warning(self, "Profile import failed", str(exc))
            return
        self.matrix_unsaved = True
        self.current_row = len(self.matrix.variants) - 1
        self._refresh_variant_list()
        self.matrix_status.setText(f"Imported {len(imported)} profile(s); save to keep them.")

    def _add_builtin_preset(self) -> None:
        if self.dirty and not self._save_current_variant():
            return
        try:
            presets = load_builtin_presets()
        except MatrixError as exc:
            QMessageBox.critical(self, "Could not load presets", str(exc))
            return
        choices = [f"{preset.variant.name}: {preset.description}" for preset in presets]
        selected, ok = QInputDialog.getItem(
            self,
            "Add built-in preset",
            "Choose a starting variant:",
            choices,
            0,
            False,
        )
        if not ok:
            return
        preset = presets[choices.index(selected)]
        base_name = preset.variant.name
        name = base_name
        suffix = 2
        while any(item.name.casefold() == name.casefold() for item in self.matrix.variants):
            name = f"{base_name} {suffix}"
            suffix += 1
        variant = BuildVariant.from_mapping({**asdict(preset.variant), "name": name})
        self.matrix.variants.append(variant)
        self.matrix_unsaved = True
        self.current_row = len(self.matrix.variants) - 1
        self._refresh_variant_list()
        self.matrix_status.setText(f"Added preset '{name}'; save to keep it.")

    def _import_overlay_targets(self) -> None:
        if self.current_row < 0:
            return
        if self.dirty and not self._save_current_variant():
            return
        directory = QFileDialog.getExistingDirectory(self, "Select a Gentoo overlay")
        if not directory:
            return
        try:
            targets = import_overlay_targets(Path(directory))
        except ProfileImportError as exc:
            QMessageBox.warning(self, "Overlay import failed", str(exc))
            return
        editor = self.config_inputs["targets"]
        existing = [line.strip() for line in editor.toPlainText().splitlines() if line.strip()]
        added = [target for target in targets if target not in existing]
        editor.setPlainText("\n".join([*existing, *added]))
        self.dirty = True
        self.matrix_status.setText(f"Found {len(targets)} overlay targets; {len(added)} added to this variant.")

    def _import_config_files(self) -> None:
        if self.current_row < 0:
            return
        if self.dirty and not self._save_current_variant():
            return
        filenames, _ = QFileDialog.getOpenFileNames(self, "Import Gentoo configuration files")
        if not filenames:
            return
        try:
            imported = import_config_files([Path(filename) for filename in filenames])
        except ProfileImportError as exc:
            QMessageBox.warning(self, "Configuration import failed", str(exc))
            return
        for field, content in imported.items():
            editor = self.config_inputs[field]
            existing = editor.toPlainText().splitlines()
            additions = [line for line in content.splitlines() if line not in existing]
            if additions:
                editor.setPlainText("\n".join([*existing, *additions]))
                self.dirty = True
        self.matrix_status.setText(f"Imported configuration from {len(filenames)} file(s); save to keep it.")

    def _new_variant(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "New empty variant",
            "Variant name:",
            QLineEdit.EchoMode.Normal,
            "Empty",
        )
        if not ok:
            return
        if self.dirty and not self._save_current_variant():
            return
        variant = BuildVariant(name=name.strip())
        try:
            BuildMatrix([*self.matrix.variants, variant]).validate()
        except MatrixError as exc:
            QMessageBox.warning(self, "Invalid variant", str(exc))
            return
        self.matrix.variants.append(variant)
        self.matrix_unsaved = True
        self.current_row = len(self.matrix.variants) - 1
        self._refresh_variant_list()

    def _duplicate_variant(self) -> None:
        if self.current_row < 0:
            return
        if self.dirty and not self._save_current_variant():
            return
        source = self.matrix.variants[self.current_row]
        base_name = f"{source.name} copy"
        name = base_name
        suffix = 2
        while any(item.name.casefold() == name.casefold() for item in self.matrix.variants):
            name = f"{base_name} {suffix}"
            suffix += 1
        duplicate = BuildVariant.from_mapping({**asdict(source), "name": name})
        self.matrix.variants.append(duplicate)
        self.matrix_unsaved = True
        self.current_row = len(self.matrix.variants) - 1
        self._refresh_variant_list()

    def _remove_variant(self) -> None:
        if self.current_row < 0 or len(self.matrix.variants) == 1:
            QMessageBox.information(self, "Cannot remove variant", "The matrix must keep at least one variant.")
            return
        name = self.matrix.variants[self.current_row].name
        answer = QMessageBox.question(
            self,
            "Remove variant",
            f"Remove '{name}' from this matrix? Any unsaved edits to it will be discarded.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.matrix.variants.pop(self.current_row)
        self.matrix_unsaved = True
        self.current_row = min(self.current_row, len(self.matrix.variants) - 1)
        self.dirty = False
        self._refresh_variant_list()

    def _selected_ai_variants(self) -> list[BuildVariant]:
        indexes = sorted(self.ai_variant_list.row(item) for item in self.ai_variant_list.selectedItems())
        return [self.matrix.variants[index] for index in indexes]

    def _refresh_ai_preview(self) -> None:
        variants = self._selected_ai_variants()
        if not variants:
            self.ai_preview.clear()
            return
        goal = self.goal_input.text() if hasattr(self, "goal_input") else ""
        model = self.model_input.text() if hasattr(self, "model_input") else ""
        if not goal.strip() or not model.strip():
            self.ai_preview.setPlainText(json.dumps(
                {"goal": goal, "model": model, "selected_variants": [asdict(item) for item in variants]},
                indent=2,
            ))
            return
        try:
            payload = build_request_payload(goal, variants, model)
        except AssistantError:
            payload = {"selected_variants": [asdict(item) for item in variants]}
        self.ai_preview.setPlainText(json.dumps(payload, indent=2))

    def _send_ai_request(self) -> None:
        if self.dirty and not self._save_current_variant():
            return
        variants = self._selected_ai_variants()
        try:
            payload = build_request_payload(self.goal_input.text(), variants, self.model_input.text())
        except AssistantError as exc:
            QMessageBox.warning(self, "AI request incomplete", str(exc))
            return
        preview = json.dumps(payload, indent=2)
        answer = QMessageBox.question(
            self,
            "Send selected context to local model",
            f"Send this request to {self.endpoint_input.text()}?\n\n"
            "Only the selected variants and the written goal are included. The response is a draft.\n\n"
            f"Request preview:\n{preview[:3000]}",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        worker = _DraftWorker(
            self.endpoint_input.text(),
            self.model_input.text(),
            self.goal_input.text(),
            variants,
        )
        worker.signals.succeeded.connect(self._draft_succeeded)
        worker.signals.failed.connect(self._draft_failed)
        self.workers.append(worker)
        self.ai_status.setText("Waiting for local model...")
        self.pool.start(worker)

    @pyqtSlot(object, str)
    def _draft_succeeded(self, worker: _DraftWorker, result: str) -> None:
        self.ai_result.setPlainText(result)
        self.ai_status.setText("Draft received; no changes were applied.")
        self.workers.remove(worker)

    @pyqtSlot(object, str)
    def _draft_failed(self, worker: _DraftWorker, message: str) -> None:
        self.ai_status.setText("Request failed.")
        self.workers.remove(worker)
        QMessageBox.warning(self, "Local AI error", message)

    def _refresh_domains(self) -> None:
        try:
            domains = list_domains()
        except VMBackendError as exc:
            self.vm_status.setText(str(exc))
            self.domain_table.setRowCount(0)
            return
        self.domain_table.setRowCount(len(domains))
        for row, domain in enumerate(domains):
            for column, value in enumerate((domain.name, domain.state, domain.uuid)):
                self.domain_table.setItem(row, column, QTableWidgetItem(value))
        self.vm_status.setText(f"Read {len(domains)} guest(s) from qemu:///system.")

    def _refresh_queue_preview(self) -> None:
        if self.dirty and not self._save_current_variant():
            return
        try:
            jobs = []
            for variant in self.matrix.variants:
                targets = dict.fromkeys(
                    line.strip() for line in variant.targets.splitlines() if line.strip()
                )
                for target in targets:
                    jobs.append(BuildJob(
                        job_id=f"{variant.name}:{target}",
                        variant_name=variant.name,
                        target=target,
                        vcpus=variant.vcpus,
                        memory_mib=variant.memory_mib,
                    ))
            budget = ResourceBudget(self.budget_vcpus.value(), self.budget_memory.value())
            ready = select_startable_jobs(jobs, [], budget)
        except MatrixError as exc:
            QMessageBox.warning(self, "Could not plan queue", str(exc))
            return
        ready_ids = {job.job_id for job in ready}
        self.queue_table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            values = (
                "Fits now" if job.job_id in ready_ids else "Queued",
                job.variant_name,
                job.target,
                str(job.vcpus),
                f"{job.memory_mib} MiB",
            )
            for column, value in enumerate(values):
                self.queue_table.setItem(row, column, QTableWidgetItem(value))
        self.queue_status.setText(
            f"{len(ready)} of {len(jobs)} build(s) fit this budget now. "
            "No VMs were started."
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.dirty or self.matrix_unsaved:
            answer = QMessageBox.question(
                self,
                "Unsaved matrix",
                "Save matrix changes before exiting?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self._save_matrix()
                if self.dirty or self.matrix_unsaved:
                    event.ignore()
                    return
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except (MatrixError, OSError) as exc:
        QMessageBox.critical(None, "Could not load build matrix", str(exc))
        raise SystemExit(1) from exc
    window.show()
    raise SystemExit(app.exec())
