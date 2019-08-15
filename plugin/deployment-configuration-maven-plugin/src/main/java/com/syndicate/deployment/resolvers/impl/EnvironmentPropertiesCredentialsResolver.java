package com.syndicate.deployment.resolvers.impl;

import com.syndicate.deployment.model.api.request.Credentials;
import com.syndicate.deployment.resolvers.AbstractChainedCredentialResolver;

import java.util.Objects;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public class EnvironmentPropertiesCredentialsResolver extends AbstractChainedCredentialResolver {

	private static final String SYNDICATE_USER_LOGIN = "SYNDICATE_USER_LOGIN";
	private static final String SYNDICATE_USER_PASS = "SYNDICATE_USER_PASS";

	@Override
	public Credentials resolveCredentials() {
		// check env vars
		String email = System.getenv(SYNDICATE_USER_LOGIN);
		if (email != null) {
			String pass = System.getenv(SYNDICATE_USER_PASS);
			Objects.requireNonNull(pass, String.format("%s has not been set", SYNDICATE_USER_PASS));
			return new Credentials(email, pass);
		}
		return null;
	}
}
