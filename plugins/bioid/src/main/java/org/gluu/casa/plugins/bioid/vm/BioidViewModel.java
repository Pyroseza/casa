package org.gluu.casa.plugins.bioid.vm;

import java.util.List;

import org.gluu.casa.credential.BasicCredential;
import org.gluu.casa.misc.Utils;
import org.gluu.casa.plugins.bioid.BioIDService;
import org.gluu.casa.plugins.bioid.model.BioIDCredential;
import org.gluu.casa.service.ISessionContext;
import org.gluu.casa.ui.UIUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.zkoss.bind.BindUtils;
import org.zkoss.bind.annotation.AfterCompose;
import org.zkoss.bind.annotation.Command;
import org.zkoss.bind.annotation.ContextParam;
import org.zkoss.bind.annotation.ContextType;
import org.zkoss.bind.annotation.Init;
import org.zkoss.bind.annotation.NotifyChange;
import org.zkoss.util.Pair;
import org.zkoss.util.resource.Labels;
import org.zkoss.zk.au.out.AuInvoke;
import org.zkoss.zk.ui.Component;
import org.zkoss.zk.ui.Executions;
import org.zkoss.zk.ui.event.Event;
import org.zkoss.zk.ui.select.Selectors;
import org.zkoss.zk.ui.select.annotation.Listen;
import org.zkoss.zk.ui.select.annotation.WireVariable;
import org.zkoss.zk.ui.util.Clients;
import org.zkoss.zul.Messagebox;

public class BioidViewModel {
	private Logger logger = LoggerFactory.getLogger(getClass());
	@WireVariable
	private ISessionContext sessionContext;
	private List<BioIDCredential> devices;
	private BioIDCredential newDevice;
	private String accessToken;
	private String apiUrl;
	private String task;
	private String trait;

	public String getAccessToken() {
		return accessToken;
	}

	public void setAccessToken(String accessToken) {
		this.accessToken = accessToken;
	}

	public String getApiUrl() {
		return apiUrl;
	}

	public void setApiUrl(String apiUrl) {
		this.apiUrl = apiUrl;
	}

	public String getTask() {
		return task;
	}

	public void setTask(String task) {
		this.task = task;
	}

	public String getTrait() {
		return trait;
	}

	public void setTrait(String trait) {
		this.trait = trait;
	}

	public BioIDCredential getNewDevice() {
		return newDevice;
	}

	public void setNewDevice(BioIDCredential newDevice) {
		this.newDevice = newDevice;
	}

	public List<BioIDCredential> getDevices() {
		return devices;
	}

	/**
	 * Initialization method for this ViewModel.
	 */
	@Init
	public void init() {
		logger.debug("init invoked");
		sessionContext = Utils.managedBean(ISessionContext.class);
		devices = BioIDService.getInstance().getBioIDDevices(sessionContext.getLoggedUser().getId());
		try {
			sessionContext = Utils.managedBean(ISessionContext.class);
			apiUrl = BioIDService.getInstance().getScriptPropertyValue("ENDPOINT");
			trait = BioIDService.TRAIT_FACE_PERIOCULAR;

			String bcid = BioIDService.getInstance().getScriptPropertyValue("STORAGE") + "."
					+ BioIDService.getInstance().getScriptPropertyValue("PARTITION") + "."
					+ sessionContext.getLoggedUser().getUserName().hashCode();
			try {
				if (BioIDService.getInstance().isEnrolled(bcid, BioIDService.TRAIT_FACE)
						&& BioIDService.getInstance().isEnrolled(bcid, BioIDService.TRAIT_PERIOCULAR)) {
					accessToken = BioIDService.getInstance().getAccessToken(bcid, BioIDService.TASK_VERIFY);

					task = BioIDService.TASK_VERIFY;
				} else {
					accessToken = BioIDService.getInstance().getAccessToken(bcid, BioIDService.TASK_ENROLL);
					task = BioIDService.TASK_ENROLL;
				}
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			// values for task for the UI API are - enrollment , verification,
			// identification and livenessdetection
			/*
			 * Clients.response(new AuInvoke("initPage", accessToken, trait,
			 * BioIDService.TASK_ENROLL.equals(task) ? "enrollment" : "verification",
			 * apiUrl, Executions.getCurrent().getContextPath())); Clients.scrollBy(0, 10);
			 */

		} catch (Exception e) {
			UIUtils.showMessageUI(false);
			logger.error(e.getMessage(), e);
		}
	}

	@Command
	public void show(String mode) {
		logger.debug("showBioID");
		try {
			sessionContext = Utils.managedBean(ISessionContext.class);
			apiUrl = BioIDService.getInstance().getScriptPropertyValue("ENDPOINT");
			trait = BioIDService.TRAIT_FACE_PERIOCULAR;

			String bcid = BioIDService.getInstance().getScriptPropertyValue("STORAGE") + "."
					+ BioIDService.getInstance().getScriptPropertyValue("PARTITION") + "."
					+ sessionContext.getLoggedUser().getUserName().hashCode();
			try {
				/*
				 * if (BioIDService.getInstance().isEnrolled(bcid, BioIDService.TRAIT_FACE) &&
				 * BioIDService.getInstance().isEnrolled(bcid, BioIDService.TRAIT_PERIOCULAR)) {
				 * accessToken = BioIDService.getInstance().getAccessToken(bcid,
				 * BioIDService.TASK_VERIFY);
				 * 
				 * task = BioIDService.TASK_VERIFY; } else {
				 */
				accessToken = BioIDService.getInstance().getAccessToken(bcid, BioIDService.TASK_ENROLL);
				task = BioIDService.TASK_ENROLL;
				/*
				 * }
				 */
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			// values for task for the UI API are - enrollment , verification,
			// identification and livenessdetection
			Clients.response(new AuInvoke("initPage", accessToken, trait,
					BioIDService.TASK_ENROLL.equals(task) ? "enrollment" : "verification", apiUrl,
					Executions.getCurrent().getContextPath()));
			Clients.scrollBy(0, 10);

		} catch (Exception e) {
			UIUtils.showMessageUI(false);
			logger.error(e.getMessage(), e);
		}

	}

	Pair<String, String> getDeleteMessages(String nick, String extraMessage) {

		StringBuilder text = new StringBuilder();
		if (extraMessage != null) {
			text.append(extraMessage).append("\n\n");
		}
		text.append(Labels.getLabel("bioid_del_confirm",
				new String[] { nick == null ? Labels.getLabel("general.no_named") : nick }));
		if (extraMessage != null) {
			text.append("\n");
		}

		return new Pair<>(Labels.getLabel("bioid_del_title"), text.toString());

	}

	@Command
	public void delete() {
		logger.debug("delete invoked");
		Pair<String, String> delMessages = getDeleteMessages(Labels.getLabel("face_periocular_traits"), null);
		Messagebox.show(delMessages.getY(), delMessages.getX(), Messagebox.YES | Messagebox.NO,
				true ? Messagebox.EXCLAMATION : Messagebox.QUESTION, event -> {
					if (Messagebox.ON_YES.equals(event.getName())) {
						boolean success = false;
						try {
							sessionContext = Utils.managedBean(ISessionContext.class);
							apiUrl = BioIDService.getInstance().getScriptPropertyValue("ENDPOINT");
							trait = BioIDService.TRAIT_FACE_PERIOCULAR;

							String bcid = BioIDService.getInstance().getScriptPropertyValue("STORAGE") + "."
									+ BioIDService.getInstance().getScriptPropertyValue("PARTITION") + "."
									+ sessionContext.getLoggedUser().getUserName().hashCode();
							try {
								success = BioIDService.getInstance()
										.deleteBioIDCredential(sessionContext.getLoggedUser().getUserName());
								if (success) {
									BioIDService.getInstance().removeFromPersistence(bcid,
											BioIDService.TRAIT_FACE_PERIOCULAR, sessionContext.getLoggedUser().getId());
								}
							} catch (Exception e) {
								// TODO Auto-generated catch block
								e.printStackTrace();
							}

						} catch (Exception e) {
							UIUtils.showMessageUI(false);
							logger.error(e.getMessage(), e);
						}
						if (success == false) {
							UIUtils.showMessageUI(false);
						} else {
							
							UIUtils.showMessageUI(true);
							Executions.sendRedirect(null);
						}

					}
				});

	}

	@Listen("onEdit=#editButton")
	public void onEdit(Event event) throws Exception {
		logger.trace(" onEdit invoked");
		persistEnrollment();
	}

	private boolean persistEnrollment() throws Exception {
		logger.debug("persistEnrollment onData=#readyButton");
		String bcid = BioIDService.getInstance().getScriptPropertyValue("STORAGE") + "."
				+ BioIDService.getInstance().getScriptPropertyValue("PARTITION") + "."
				+ sessionContext.getLoggedUser().getUserName().hashCode();
		boolean success = BioIDService.getInstance().writeToPersistence(bcid, "enroll",
				BioIDService.TRAIT_FACE_PERIOCULAR, sessionContext.getLoggedUser().getId());
		logger.debug("persistEnrollment onData=#readyButton : " + success);
		return success;
	}

	@Listen("onData=#readyButton")
	public void onData(Event event) throws Exception {
		logger.trace(" onData invoked");
		persistEnrollment();
	}

	@AfterCompose
	public void afterCompose(@ContextParam(ContextType.VIEW) Component view) {
		Selectors.wireEventListeners(view, this);
	}
}